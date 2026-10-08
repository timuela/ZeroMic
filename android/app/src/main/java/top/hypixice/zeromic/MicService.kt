package top.hypixice.zeromic

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.net.wifi.WifiManager
import android.os.Binder
import android.os.IBinder
import android.os.PowerManager
import androidx.core.app.NotificationCompat
import androidx.core.app.ServiceCompat
import androidx.core.content.ContextCompat
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import top.hypixice.zeromic.signaling.SignalingClient
import top.hypixice.zeromic.webrtc.WebRtcClient

enum class MicPhase { IDLE, CONNECTING, STREAMING, ERROR }

data class MicState(
    val phase: MicPhase = MicPhase.IDLE,
    val muted: Boolean = false,
    val gain: Float = 1f,
    val error: String? = null
)

class MicService : Service(), SignalingClient.Listener, WebRtcClient.Listener {

    private val binder = LocalBinder()
    private val _state = MutableStateFlow(MicState())
    val state: StateFlow<MicState> = _state.asStateFlow()

    private var signaling: SignalingClient? = null
    private var webRtc: WebRtcClient? = null
    private var wakeLock: PowerManager.WakeLock? = null
    private var wifiLock: WifiManager.WifiLock? = null

    @Volatile private var muted = false

    inner class LocalBinder : Binder() {
        fun service(): MicService = this@MicService
    }

    override fun onBind(intent: Intent?): IBinder = binder

    override fun onCreate() {
        super.onCreate()
        createChannel()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_STOP -> {
                teardown()
                ServiceCompat.stopForeground(this, ServiceCompat.STOP_FOREGROUND_REMOVE)
                stopSelf()
                return START_NOT_STICKY
            }

            ACTION_TOGGLE_MUTE -> {
                if (signaling != null) toggleMute()
            }

            else -> {
                val address = intent?.getStringExtra(EXTRA_ADDRESS) ?: ""
                val gain = intent?.getFloatExtra(EXTRA_GAIN, 1f) ?: 1f
                startForegroundCompat()
                beginSession(address, gain)
            }
        }
        return START_STICKY
    }

    override fun onDestroy() {
        teardown()
        super.onDestroy()
    }

    fun setGainFromUi(gain: Float) {
        _state.value = _state.value.copy(gain = gain)
        webRtc?.setGain(gain)
    }

    fun toggleMuteFromUi() {
        if (signaling != null) toggleMute()
    }

    private fun toggleMute() {
        muted = !muted
        webRtc?.setMuted(muted)
        _state.value = _state.value.copy(muted = muted)
        notifyState()
    }

    private fun beginSession(address: String, gain: Float) {
        val parsed = parseAddress(address)
        if (parsed == null) {
            _state.value = MicState(phase = MicPhase.ERROR, gain = gain, error = getString(R.string.error_invalid_address))
            return
        }

        acquireLocks()
        muted = false
        _state.value = MicState(phase = MicPhase.CONNECTING, gain = gain)

        val (host, port) = parsed
        signaling = SignalingClient(host, port, this).also { it.connect() }
    }

    private fun teardown() {
        signaling?.disconnect()
        signaling = null
        webRtc?.shutdown()
        webRtc = null
        releaseLocks()
        muted = false
        _state.value = MicState(phase = MicPhase.IDLE)
    }

    override fun onSignalingConnected() {
        signaling?.join()
        val current = webRtc
        if (current == null) {
            val client = WebRtcClient(applicationContext, this)
            webRtc = client
            client.setGain(_state.value.gain)
            client.start()
        } else {
            current.renegotiate()
        }
    }

    override fun onSignalingDisconnected(reason: String?) {
        if (signaling != null) {
            _state.value = _state.value.copy(phase = MicPhase.CONNECTING)
        }
    }

    override fun onPeerReady() {}

    override fun onAnswer(answerSdp: String) {
        webRtc?.onAnswer(answerSdp)
    }

    override fun onRemoteCandidate(candidate: String, sdpMid: String?, sdpMLineIndex: Int) {
        webRtc?.addRemoteCandidate(candidate, sdpMid, sdpMLineIndex)
    }

    override fun onToggleMute() {
        toggleMute()
    }

    override fun onLocalSdp(sdp: String) {
        signaling?.sendOffer(sdp)
    }

    override fun onLocalCandidate(candidate: String, sdpMid: String?, sdpMLineIndex: Int) {
        signaling?.sendCandidate(candidate, sdpMid, sdpMLineIndex)
    }

    override fun onRtcState(state: WebRtcClient.State) {
        val phase = when (state) {
            WebRtcClient.State.CONNECTED -> MicPhase.STREAMING
            WebRtcClient.State.CONNECTING,
            WebRtcClient.State.DISCONNECTED,
            WebRtcClient.State.FAILED -> MicPhase.CONNECTING
        }
        _state.value = _state.value.copy(phase = phase, muted = muted)
    }

    private fun parseAddress(raw: String): Pair<String, Int>? {
        val trimmed = raw.trim().removePrefix("https://").removePrefix("http://").trimEnd('/')
        if (trimmed.isEmpty()) return null
        val parts = trimmed.split(":")
        if (parts.size != 2) return null
        val host = parts[0].trim()
        val port = parts[1].trim().toIntOrNull() ?: return null
        if (host.isEmpty() || port !in 1..65535) return null
        return host to port
    }

    @Suppress("DEPRECATION")
    private fun acquireLocks() {
        if (wakeLock == null) {
            val pm = getSystemService(Context.POWER_SERVICE) as PowerManager
            wakeLock = pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "ZeroMic::Mic").apply {
                setReferenceCounted(false)
                acquire()
            }
        }
        if (wifiLock == null) {
            val wm = applicationContext.getSystemService(Context.WIFI_SERVICE) as WifiManager
            wifiLock = wm.createWifiLock(WifiManager.WIFI_MODE_FULL_HIGH_PERF, "ZeroMic::Wifi").apply {
                setReferenceCounted(false)
                acquire()
            }
        }
    }

    private fun releaseLocks() {
        wakeLock?.let { if (it.isHeld) it.release() }
        wakeLock = null
        wifiLock?.let { if (it.isHeld) it.release() }
        wifiLock = null
    }

    private fun startForegroundCompat() {
        ServiceCompat.startForeground(
            this,
            NOTIFICATION_ID,
            buildNotification(),
            ServiceInfo.FOREGROUND_SERVICE_TYPE_MICROPHONE
        )
    }

    private fun notifyState() {
        val manager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        manager.notify(NOTIFICATION_ID, buildNotification())
    }

    private fun createChannel() {
        val manager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        val channel = NotificationChannel(
            CHANNEL_ID,
            getString(R.string.notification_channel_name),
            NotificationManager.IMPORTANCE_LOW
        ).apply {
            description = getString(R.string.notification_channel_desc)
            setShowBadge(false)
        }
        manager.createNotificationChannel(channel)
    }

    private fun buildNotification(): Notification {
        val flags = PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
        val contentIntent = PendingIntent.getActivity(
            this, 0, Intent(this, MainActivity::class.java), flags
        )
        val muteIntent = PendingIntent.getService(
            this, 1, Intent(this, MicService::class.java).setAction(ACTION_TOGGLE_MUTE), flags
        )
        val stopIntent = PendingIntent.getService(
            this, 2, Intent(this, MicService::class.java).setAction(ACTION_STOP), flags
        )
        val muteLabel = getString(
            if (muted) R.string.notification_action_unmute else R.string.notification_action_mute
        )
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setSmallIcon(R.drawable.ic_stat_mic)
            .setContentTitle(getString(R.string.notification_title))
            .setContentText(getString(R.string.notification_text))
            .setContentIntent(contentIntent)
            .setOngoing(true)
            .setOnlyAlertOnce(true)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .addAction(0, muteLabel, muteIntent)
            .addAction(0, getString(R.string.disconnect), stopIntent)
            .build()
    }

    companion object {
        const val ACTION_START = "top.hypixice.zeromic.START"
        const val ACTION_STOP = "top.hypixice.zeromic.STOP"
        const val ACTION_TOGGLE_MUTE = "top.hypixice.zeromic.TOGGLE_MUTE"
        const val EXTRA_ADDRESS = "address"
        const val EXTRA_GAIN = "gain"

        private const val CHANNEL_ID = "zeromic_mic"
        private const val NOTIFICATION_ID = 1

        fun start(context: Context, address: String, gain: Float) {
            val intent = Intent(context, MicService::class.java).apply {
                action = ACTION_START
                putExtra(EXTRA_ADDRESS, address)
                putExtra(EXTRA_GAIN, gain)
            }
            ContextCompat.startForegroundService(context, intent)
        }

        fun stop(context: Context) {
            val intent = Intent(context, MicService::class.java).apply { action = ACTION_STOP }
            runCatching { context.startService(intent) }
        }
    }
}

package top.hypixice.zeromic.signaling

import io.socket.client.IO
import io.socket.client.Socket
import okhttp3.OkHttpClient
import org.json.JSONObject
import java.net.URI
import java.security.SecureRandom
import java.security.cert.X509Certificate
import java.util.concurrent.TimeUnit
import javax.net.ssl.SSLContext
import javax.net.ssl.TrustManager
import javax.net.ssl.X509TrustManager

class SignalingClient(
    private val host: String,
    private val port: Int,
    private val listener: Listener
) {
    interface Listener {
        fun onSignalingConnected()
        fun onSignalingDisconnected(reason: String?)
        fun onAnswer(answerSdp: String)
        fun onRemoteCandidate(candidate: String, sdpMid: String?, sdpMLineIndex: Int)
        fun onPeerReady()
        fun onToggleMute()
    }

    private var socket: Socket? = null

    fun connect() {
        if (socket != null) return

        val client = buildTrustAllClient()
        val options = IO.Options().apply {
            reconnection = true
            callFactory = client
            webSocketFactory = client
        }

        val s = IO.socket(URI("https://$host:$port"), options)

        s.on(Socket.EVENT_CONNECT) { _ ->
            listener.onSignalingConnected()
        }
        s.on(Socket.EVENT_DISCONNECT) { args ->
            listener.onSignalingDisconnected(args.firstOrNull() as? String)
        }
        s.on(Socket.EVENT_CONNECT_ERROR) { args ->
            listener.onSignalingDisconnected(args.firstOrNull()?.toString())
        }
        s.on("ready") { _ ->
            listener.onPeerReady()
        }
        s.on("answer") { args ->
            val obj = args.firstOrNull() as? JSONObject
            if (obj != null) {
                val sdp = obj.optString("sdp")
                if (sdp.isNotEmpty()) listener.onAnswer(sdp)
            }
        }
        s.on("ice_candidate") { args ->
            val obj = args.firstOrNull() as? JSONObject
            if (obj != null) {
                val candidate = obj.optString("candidate")
                if (candidate.isNotEmpty()) {
                    val mid = if (obj.isNull("sdpMid")) null else obj.optString("sdpMid", null)
                    listener.onRemoteCandidate(candidate, mid, obj.optInt("sdpMLineIndex", 0))
                }
            }
        }
        s.on("toggle_mute") { _ ->
            listener.onToggleMute()
        }

        socket = s
        s.connect()
    }

    fun join() {
        socket?.emit("join", JSONObject().put("role", "mobile"))
    }

    fun sendOffer(sdp: String) {
        socket?.emit("offer", JSONObject().put("type", "offer").put("sdp", sdp))
    }

    fun sendCandidate(candidate: String, sdpMid: String?, sdpMLineIndex: Int) {
        val payload = JSONObject()
            .put("candidate", candidate)
            .put("sdpMid", sdpMid ?: JSONObject.NULL)
            .put("sdpMLineIndex", sdpMLineIndex)
        socket?.emit("ice_candidate", payload)
    }

    fun disconnect() {
        val s = socket
        socket = null
        if (s != null) runCatching { s.disconnect() }
    }

    private fun buildTrustAllClient(): OkHttpClient {
        val trustAll = object : X509TrustManager {
            override fun checkClientTrusted(chain: Array<out X509Certificate>?, authType: String?) {}
            override fun checkServerTrusted(chain: Array<out X509Certificate>?, authType: String?) {}
            override fun getAcceptedIssuers(): Array<X509Certificate> = emptyArray()
        }
        val sslContext = SSLContext.getInstance("TLS")
        sslContext.init(null, arrayOf<TrustManager>(trustAll), SecureRandom())
        return OkHttpClient.Builder()
            .sslSocketFactory(sslContext.socketFactory, trustAll)
            .hostnameVerifier { _, _ -> true }
            .connectTimeout(10, TimeUnit.SECONDS)
            .readTimeout(0, TimeUnit.MILLISECONDS)
            .build()
    }
}

package top.hypixice.zeromic.data

import android.content.Context

class Prefs(context: Context) {
    private val prefs = context.applicationContext.getSharedPreferences(FILE, Context.MODE_PRIVATE)

    var address: String
        get() = prefs.getString(KEY_ADDRESS, "") ?: ""
        set(value) = prefs.edit().putString(KEY_ADDRESS, value).apply()

    var gain: Float
        get() = prefs.getFloat(KEY_GAIN, 1f)
        set(value) = prefs.edit().putFloat(KEY_GAIN, value).apply()

    companion object {
        private const val FILE = "zeromic_prefs"
        private const val KEY_ADDRESS = "address"
        private const val KEY_GAIN = "gain"
    }
}

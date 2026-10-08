package top.hypixice.zeromic

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.viewModels
import top.hypixice.zeromic.ui.MicScreen
import top.hypixice.zeromic.ui.MicViewModel
import top.hypixice.zeromic.ui.theme.ZeroMicTheme

class MainActivity : ComponentActivity() {

    private val viewModel: MicViewModel by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            ZeroMicTheme {
                MicScreen(viewModel)
            }
        }
    }

    override fun onStart() {
        super.onStart()
        viewModel.bind()
    }

    override fun onStop() {
        viewModel.unbind()
        super.onStop()
    }
}

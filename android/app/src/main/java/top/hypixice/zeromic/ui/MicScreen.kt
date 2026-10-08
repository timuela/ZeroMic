package top.hypixice.zeromic.ui

import android.Manifest
import android.content.pm.PackageManager
import android.os.Build
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Mic
import androidx.compose.material.icons.filled.MicOff
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.Stop
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Slider
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.content.ContextCompat
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import top.hypixice.zeromic.MicPhase
import top.hypixice.zeromic.MicState
import top.hypixice.zeromic.R
import top.hypixice.zeromic.data.HostProfile

@Composable
fun MicScreen(viewModel: MicViewModel) {
    val context = LocalContext.current
    val state by viewModel.state.collectAsStateWithLifecycle()
    var errorText by remember { mutableStateOf<String?>(null) }
    var hostsOpen by remember { mutableStateOf(false) }

    val runtimePermissions = remember {
        buildList {
            add(Manifest.permission.RECORD_AUDIO)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                add(Manifest.permission.POST_NOTIFICATIONS)
            }
        }.toTypedArray()
    }

    val permissionLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { result ->
        if (result[Manifest.permission.RECORD_AUDIO] == true) {
            errorText = null
            viewModel.connect()
        } else {
            errorText = context.getString(R.string.error_mic_permission)
        }
    }

    fun startSession() {
        val micGranted = ContextCompat.checkSelfPermission(
            context, Manifest.permission.RECORD_AUDIO
        ) == PackageManager.PERMISSION_GRANTED
        if (micGranted) {
            errorText = null
            viewModel.connect()
        } else {
            permissionLauncher.launch(runtimePermissions)
        }
    }

    val active = state.phase == MicPhase.STREAMING || state.phase == MicPhase.CONNECTING

    Scaffold(containerColor = MaterialTheme.colorScheme.background) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(horizontal = 24.dp, vertical = 16.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Icon(
                    imageVector = Icons.Filled.Mic,
                    contentDescription = null,
                    tint = MaterialTheme.colorScheme.primary
                )
                Spacer(Modifier.size(8.dp))
                Text(
                    text = stringResource(R.string.app_name),
                    fontSize = 20.sp,
                    fontWeight = FontWeight.Medium,
                    color = MaterialTheme.colorScheme.onBackground
                )
            }

            Spacer(Modifier.height(24.dp))

            StatusCard(state)

            Spacer(Modifier.height(24.dp))

            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Box {
                    OutlinedButton(onClick = { hostsOpen = true }, enabled = !active) {
                        Text("${stringResource(R.string.hosts)} (${viewModel.profiles.size})")
                    }
                    DropdownMenu(
                        expanded = hostsOpen,
                        onDismissRequest = { hostsOpen = false }
                    ) {
                        if (viewModel.profiles.isEmpty()) {
                            DropdownMenuItem(
                                text = { Text(stringResource(R.string.hosts_empty)) },
                                onClick = {},
                                enabled = false
                            )
                        }
                        viewModel.profiles.forEach { profile ->
                            DropdownMenuItem(
                                text = { Text(profile.address) },
                                onClick = {
                                    viewModel.selectProfile(profile)
                                    hostsOpen = false
                                }
                            )
                        }
                        HorizontalDivider()
                        DropdownMenuItem(
                            text = { Text(stringResource(R.string.host_save)) },
                            enabled = viewModel.address.isNotBlank(),
                            leadingIcon = {
                                Icon(Icons.Filled.Add, contentDescription = null)
                            },
                            onClick = {
                                viewModel.saveCurrentProfile()
                                hostsOpen = false
                            }
                        )
                        if (viewModel.hasProfileFor(viewModel.address)) {
                            val current = viewModel.address.trim()
                            DropdownMenuItem(
                                text = { Text(stringResource(R.string.host_delete)) },
                                leadingIcon = {
                                    Icon(Icons.Filled.Delete, contentDescription = null)
                                },
                                onClick = {
                                    viewModel.deleteProfile(HostProfile(current, current))
                                    hostsOpen = false
                                }
                            )
                        }
                    }
                }
                Spacer(Modifier.weight(1f))
            }

            Spacer(Modifier.height(12.dp))

            OutlinedTextField(
                value = viewModel.address,
                onValueChange = viewModel::onAddressChange,
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
                enabled = !active,
                label = { Text(stringResource(R.string.address_label)) },
                placeholder = { Text(stringResource(R.string.address_hint)) }
            )

            Spacer(Modifier.height(24.dp))

            Column(Modifier.fillMaxWidth()) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Text(
                        text = stringResource(R.string.gain),
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    Text(
                        text = "%.1f×".format(viewModel.gain),
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
                Slider(
                    value = viewModel.gain,
                    onValueChange = viewModel::onGainChange,
                    valueRange = 0f..3f
                )
            }

            Spacer(Modifier.weight(1f))

            Box(Modifier.size(180.dp), contentAlignment = Alignment.Center) {
                val (buttonColor, icon, tint) = micAppearance(state)
                Surface(
                    onClick = { if (active) viewModel.toggleMute() },
                    enabled = active,
                    shape = CircleShape,
                    color = buttonColor,
                    modifier = Modifier.size(140.dp)
                ) {
                    Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                        Icon(
                            imageVector = icon,
                            contentDescription = null,
                            tint = tint,
                            modifier = Modifier.size(56.dp)
                        )
                    }
                }
            }

            errorText?.let { message ->
                Text(
                    text = message,
                    color = MaterialTheme.colorScheme.error,
                    fontSize = 13.sp,
                    modifier = Modifier.padding(top = 12.dp)
                )
            }
            state.error?.let { message ->
                Text(
                    text = message,
                    color = MaterialTheme.colorScheme.error,
                    fontSize = 13.sp,
                    modifier = Modifier.padding(top = 12.dp)
                )
            }

            Spacer(Modifier.height(24.dp))

            Button(
                onClick = { if (active) viewModel.disconnect() else startSession() },
                modifier = Modifier
                    .fillMaxWidth()
                    .height(52.dp),
                colors = if (active) {
                    ButtonDefaults.buttonColors(
                        containerColor = MaterialTheme.colorScheme.surfaceVariant,
                        contentColor = MaterialTheme.colorScheme.onSurface
                    )
                } else {
                    ButtonDefaults.buttonColors()
                }
            ) {
                Icon(
                    imageVector = if (active) Icons.Filled.Stop else Icons.Filled.PlayArrow,
                    contentDescription = null
                )
                Spacer(Modifier.size(8.dp))
                Text(
                    text = stringResource(if (active) R.string.disconnect else R.string.connect),
                    fontSize = 16.sp
                )
            }

            Spacer(Modifier.height(8.dp))
        }
    }
}

@Composable
private fun StatusCard(state: MicState) {
    Surface(
        color = MaterialTheme.colorScheme.surface,
        shape = MaterialTheme.shapes.large,
        modifier = Modifier.fillMaxWidth()
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 20.dp, vertical = 16.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Text(
                text = stringResource(R.string.host_status),
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                fontSize = 12.sp
            )
            val (label, color) = statusAppearance(state)
            Row(verticalAlignment = Alignment.CenterVertically) {
                Surface(color = color, shape = CircleShape, modifier = Modifier.size(10.dp)) {}
                Spacer(Modifier.size(8.dp))
                Text(text = label, color = color, fontWeight = FontWeight.SemiBold)
            }
        }
    }
}

@Composable
private fun statusAppearance(state: MicState): Pair<String, Color> {
    return when (state.phase) {
        MicPhase.IDLE -> stringResource(R.string.status_idle) to MaterialTheme.colorScheme.onSurfaceVariant
        MicPhase.CONNECTING -> stringResource(R.string.status_connecting) to Color(0xFFFF9800)
        MicPhase.STREAMING -> if (state.muted) {
            stringResource(R.string.status_muted) to Color(0xFFFFB3AE)
        } else {
            stringResource(R.string.status_streaming) to Color(0xFF4CAF50)
        }
        MicPhase.ERROR -> stringResource(R.string.status_error) to MaterialTheme.colorScheme.error
    }
}

@Composable
private fun micAppearance(state: MicState): Triple<Color, ImageVector, Color> {
    return when {
        state.phase == MicPhase.IDLE -> Triple(
            MaterialTheme.colorScheme.surfaceVariant,
            Icons.Filled.Mic,
            MaterialTheme.colorScheme.onSurfaceVariant
        )
        state.muted -> Triple(
            Color(0xFFFFB3AE),
            Icons.Filled.MicOff,
            Color(0xFF4A0005)
        )
        else -> Triple(
            MaterialTheme.colorScheme.primary,
            Icons.Filled.Mic,
            MaterialTheme.colorScheme.onPrimary
        )
    }
}

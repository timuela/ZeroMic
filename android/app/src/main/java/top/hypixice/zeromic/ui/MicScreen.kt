package top.hypixice.zeromic.ui

import android.Manifest
import android.content.pm.PackageManager
import android.os.Build
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.ExperimentalFoundationApi
import androidx.compose.foundation.combinedClickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Mic
import androidx.compose.material.icons.filled.MicOff
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.Stop
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Slider
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
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
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.content.ContextCompat
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import top.hypixice.zeromic.BuildConfig
import top.hypixice.zeromic.MicPhase
import top.hypixice.zeromic.MicState
import top.hypixice.zeromic.R
import top.hypixice.zeromic.data.HostProfile
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.slideInHorizontally
import androidx.compose.animation.slideOutHorizontally
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.BoxScope
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.width
import androidx.compose.material.icons.filled.ArrowDropDown
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Menu
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.IconButton

@Composable
fun MicScreen(viewModel: MicViewModel, onLanguageChanged: () -> Unit = {}) {
    val context = LocalContext.current
    val state by viewModel.state.collectAsStateWithLifecycle()
    var errorText by remember { mutableStateOf<String?>(null) }
    var addHostOpen by remember { mutableStateOf(false) }
    var pendingDelete by remember { mutableStateOf<HostProfile?>(null) }
    var settingsOpen by remember { mutableStateOf(false) }

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

    Box(Modifier.fillMaxSize()) {
    Scaffold(containerColor = MaterialTheme.colorScheme.background) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
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
                Spacer(Modifier.size(6.dp))
                Text(
                    text = BuildConfig.VERSION_NAME,
                    fontSize = 11.sp,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                Spacer(Modifier.weight(1f))
                IconButton(onClick = { settingsOpen = true }) {
                    Icon(
                        imageVector = Icons.Filled.Menu,
                        contentDescription = stringResource(R.string.settings_title),
                        tint = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }

            Spacer(Modifier.height(24.dp))

            StatusCard(state)

            Spacer(Modifier.height(24.dp))

            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = stringResource(R.string.hosts),
                    fontSize = 12.sp,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                Spacer(Modifier.weight(1f))
                OutlinedButton(onClick = { addHostOpen = true }, enabled = !active) {
                    Icon(
                        imageVector = Icons.Filled.Add,
                        contentDescription = null,
                        modifier = Modifier.size(18.dp)
                    )
                    Spacer(Modifier.size(6.dp))
                    Text(stringResource(R.string.host_add))
                }
            }

            Spacer(Modifier.height(8.dp))

            if (viewModel.profiles.isEmpty()) {
                Text(
                    text = stringResource(R.string.hosts_empty),
                    fontSize = 12.sp,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            } else {
                LazyVerticalGrid(
                    columns = GridCells.Fixed(3),
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(116.dp),
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp),
                    userScrollEnabled = !active
                ) {
                    items(viewModel.profiles, key = { it.address }) { profile ->
                        HostCard(
                            profile = profile,
                            selected = profile.address == viewModel.address.trim(),
                            onClick = { viewModel.selectProfile(profile) },
                            onLongClick = { pendingDelete = profile }
                        )
                    }
                }
                Spacer(Modifier.height(4.dp))
                Text(
                    text = stringResource(R.string.host_delete_hint),
                    fontSize = 10.sp,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
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

            Spacer(Modifier.height(12.dp))

            OutlinedTextField(
                value = viewModel.pin,
                onValueChange = viewModel::onPinChange,
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
                enabled = !active,
                label = { Text(stringResource(R.string.pin_label)) },
                placeholder = { Text(stringResource(R.string.pin_hint)) }
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
                        text = stringResource(R.string.gain_value, viewModel.gain),
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
                Slider(
                    value = viewModel.gain,
                    onValueChange = viewModel::onGainChange,
                    valueRange = 0f..3f
                )
            }

            Spacer(Modifier.height(24.dp))

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

    SettingsDrawer(
        open = settingsOpen,
        language = viewModel.language,
        version = BuildConfig.VERSION_NAME,
        onLanguageSelected = { code ->
            viewModel.selectLanguage(code)
            onLanguageChanged()
        },
        onClose = { settingsOpen = false },
    )
    }

    if (addHostOpen) {
        AddHostDialog(
            initialAddress = viewModel.address.trim(),
            onDismiss = { addHostOpen = false },
            onConfirm = { name, address, description ->
                viewModel.addProfile(name, address, description)
                addHostOpen = false
            }
        )
    }

    pendingDelete?.let { profile ->
        AlertDialog(
            onDismissRequest = { pendingDelete = null },
            title = { Text(stringResource(R.string.host_delete_confirm)) },
            text = { Text(profile.name) },
            confirmButton = {
                TextButton(onClick = {
                    viewModel.deleteProfile(profile)
                    pendingDelete = null
                }) {
                    Text(stringResource(R.string.host_delete))
                }
            },
            dismissButton = {
                TextButton(onClick = { pendingDelete = null }) {
                    Text(stringResource(R.string.cancel))
                }
            }
        )
    }
}

@Composable
private fun BoxScope.SettingsDrawer(
    open: Boolean,
    language: String,
    version: String,
    onLanguageSelected: (String) -> Unit,
    onClose: () -> Unit,
) {
    AnimatedVisibility(visible = open, enter = fadeIn(), exit = fadeOut()) {
        Box(
            Modifier
                .fillMaxSize()
                .background(Color.Black.copy(alpha = 0.5f))
                .clickable { onClose() }
        )
    }
    AnimatedVisibility(
        visible = open,
        enter = slideInHorizontally(initialOffsetX = { it }),
        exit = slideOutHorizontally(targetOffsetX = { it }),
        modifier = Modifier.align(Alignment.CenterEnd),
    ) {
        SettingsPanel(language, version, onLanguageSelected, onClose)
    }
}

@Composable
private fun SettingsPanel(
    language: String,
    version: String,
    onLanguageSelected: (String) -> Unit,
    onClose: () -> Unit,
) {
    Surface(
        modifier = Modifier
            .width(300.dp)
            .fillMaxHeight(),
        color = MaterialTheme.colorScheme.surface,
        tonalElevation = 4.dp,
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(20.dp)
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text(
                    text = stringResource(R.string.settings_title),
                    fontSize = 18.sp,
                    fontWeight = FontWeight.Medium,
                    color = MaterialTheme.colorScheme.onSurface,
                )
                IconButton(onClick = onClose) {
                    Icon(
                        imageVector = Icons.Filled.Close,
                        contentDescription = stringResource(R.string.settings_close),
                        tint = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
            }

            Spacer(Modifier.height(20.dp))
            Text(
                text = stringResource(R.string.settings_language),
                fontSize = 12.sp,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            Spacer(Modifier.height(8.dp))
            LanguageSelector(language, onLanguageSelected)

            Spacer(Modifier.height(20.dp))
            Text(
                text = stringResource(R.string.settings_more),
                fontSize = 12.sp,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            Spacer(Modifier.height(8.dp))
            Text(
                text = stringResource(R.string.about_body),
                fontSize = 13.sp,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )

            Spacer(Modifier.weight(1f))
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
            ) {
                Text(
                    text = stringResource(R.string.settings_version),
                    fontSize = 12.sp,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                Text(
                    text = version,
                    fontSize = 12.sp,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        }
    }
}

@Composable
private fun LanguageSelector(current: String, onSelected: (String) -> Unit) {
    val options = listOf(
        "en" to R.string.lang_en,
        "zh" to R.string.lang_zh,
        "vi" to R.string.lang_vi,
    )
    var expanded by remember { mutableStateOf(false) }
    Box {
        OutlinedButton(onClick = { expanded = true }, modifier = Modifier.fillMaxWidth()) {
            Text(
                text = stringResource(
                    options.firstOrNull { it.first == current }?.second ?: R.string.lang_en
                )
            )
            Spacer(Modifier.weight(1f))
            Icon(imageVector = Icons.Filled.ArrowDropDown, contentDescription = null)
        }
        DropdownMenu(expanded = expanded, onDismissRequest = { expanded = false }) {
            options.forEach { (code, labelRes) ->
                DropdownMenuItem(
                    text = { Text(stringResource(labelRes)) },
                    onClick = {
                        expanded = false
                        onSelected(code)
                    },
                )
            }
        }
    }
}

@OptIn(ExperimentalFoundationApi::class)
@Composable
private fun HostCard(
    profile: HostProfile,
    selected: Boolean,
    onClick: () -> Unit,
    onLongClick: () -> Unit
) {
    Surface(
        modifier = Modifier
            .fillMaxWidth()
            .heightIn(min = 54.dp)
            .combinedClickable(onClick = onClick, onLongClick = onLongClick),
        shape = MaterialTheme.shapes.medium,
        color = if (selected) {
            MaterialTheme.colorScheme.primary.copy(alpha = 0.18f)
        } else {
            MaterialTheme.colorScheme.surfaceVariant
        },
        border = BorderStroke(
            width = 1.dp,
            color = if (selected) {
                MaterialTheme.colorScheme.primary
            } else {
                MaterialTheme.colorScheme.outline
            }
        )
    ) {
        Column(
            modifier = Modifier.padding(horizontal = 8.dp, vertical = 8.dp),
            verticalArrangement = Arrangement.spacedBy(2.dp)
        ) {
            Text(
                text = profile.name,
                fontSize = 13.sp,
                fontWeight = FontWeight.SemiBold,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
                color = MaterialTheme.colorScheme.onSurface
            )
            Text(
                text = profile.address,
                fontSize = 10.sp,
                maxLines = 1,
                softWrap = false,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
            if (profile.description.isNotBlank()) {
                Text(
                    text = profile.description,
                    fontSize = 10.sp,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        }
    }
}

@Composable
private fun AddHostDialog(
    initialAddress: String,
    onDismiss: () -> Unit,
    onConfirm: (String, String, String) -> Unit
) {
    var name by remember { mutableStateOf("") }
    var address by remember { mutableStateOf(initialAddress) }
    var description by remember { mutableStateOf("") }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(stringResource(R.string.host_add_title)) },
        text = {
            Column {
                OutlinedTextField(
                    value = name,
                    onValueChange = { name = it },
                    singleLine = true,
                    label = { Text(stringResource(R.string.host_name)) },
                    modifier = Modifier.fillMaxWidth()
                )
                Spacer(Modifier.height(8.dp))
                OutlinedTextField(
                    value = address,
                    onValueChange = { address = it },
                    singleLine = true,
                    label = { Text(stringResource(R.string.host_ip)) },
                    placeholder = { Text(stringResource(R.string.address_hint)) },
                    modifier = Modifier.fillMaxWidth()
                )
                Spacer(Modifier.height(8.dp))
                OutlinedTextField(
                    value = description,
                    onValueChange = { description = it },
                    singleLine = true,
                    label = { Text(stringResource(R.string.host_description)) },
                    modifier = Modifier.fillMaxWidth()
                )
            }
        },
        confirmButton = {
            TextButton(
                enabled = name.isNotBlank() && address.isNotBlank(),
                onClick = { onConfirm(name.trim(), address.trim(), description.trim()) }
            ) {
                Text(stringResource(R.string.host_add))
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) {
                Text(stringResource(R.string.cancel))
            }
        }
    )
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

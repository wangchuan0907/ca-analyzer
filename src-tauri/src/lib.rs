use std::sync::Mutex;

mod serial;

use serial::SerialManager;

// Global state for serial port
struct AppState {
    serial: Mutex<SerialManager>,
}

// =============================================
// Tauri Commands
// =============================================

#[tauri::command]
fn list_ports(state: tauri::State<AppState>) -> Result<Vec<String>, String> {
    state.serial.lock().unwrap().list_ports()
}

#[tauri::command]
fn open_port(path: String, state: tauri::State<AppState>) -> Result<(), String> {
    state.serial.lock().unwrap().open_port(&path)
}

#[tauri::command]
fn close_port(state: tauri::State<AppState>) -> Result<(), String> {
    state.serial.lock().unwrap().close_port()
}

#[tauri::command]
fn send_command(cmd: String, state: tauri::State<AppState>) -> Result<String, String> {
    state.serial.lock().unwrap().send_command(&cmd)
}

#[tauri::command]
fn measure_once(state: tauri::State<AppState>) -> Result<(f64, f64, f64), String> {
    state.serial.lock().unwrap().measure_once()
}

#[tauri::command]
fn write_csv_file(path: String, content: String) -> Result<(), String> {
    std::fs::write(&path, content).map_err(|e| e.to_string())
}

// =============================================
// App Entry
// =============================================

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    env_logger::Builder::from_env(env_logger::Env::default().default_filter_or("info")).init();

    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .manage(AppState {
            serial: Mutex::new(SerialManager::new()),
        })
        .invoke_handler(tauri::generate_handler![
            list_ports,
            open_port,
            close_port,
            send_command,
            measure_once,
            write_csv_file,
        ])
        .setup(|app| {
            log::info!("CA-410 灰阶亮色度测量 启动成功");
            let _ = app;
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

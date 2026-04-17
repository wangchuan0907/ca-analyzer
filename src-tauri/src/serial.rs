/**
 * Serial port manager for CA-410 Color Analyzer
 * Protocol: 38400 baud, 8N1, commands end with \r
 */

use serialport::SerialPort;
use std::io::{Read, Write};
use std::time::Duration;

pub struct SerialManager {
    port: Option<Box<dyn SerialPort>>,
}

impl SerialManager {
    pub fn new() -> Self {
        SerialManager { port: None }
    }

    pub fn list_ports(&self) -> Result<Vec<String>, String> {
        let ports = serialport::available_ports()
            .map_err(|e| e.to_string())?;

        let mut result = Vec::new();
        for p in &ports {
            let name = &p.port_name;
            // SerialPortType doesn't implement Display, use Debug format
            let desc = format!("{:?}", p.port_type);
            if desc.contains("Measuring Instruments")
                || desc.contains("USB")
                || desc.contains("COM")
            {
                result.push(name.clone());
            }
        }

        if result.is_empty() {
            for p in &ports {
                if p.port_name.starts_with("COM") {
                    result.push(p.port_name.clone());
                }
            }
        }

        Ok(result)
    }

    pub fn open_port(&mut self, path: &str) -> Result<(), String> {
        self.close_port()?;

        let port = serialport::new(path, 38_400)
            .data_bits(serialport::DataBits::Eight)
            .stop_bits(serialport::StopBits::One)
            .parity(serialport::Parity::None)
            .timeout(Duration::from_millis(3000))
            .open()
            .map_err(|e| format!("打开串口失败: {}", e))?;

        self.port = Some(port);
        log::info!("串口已打开: {}", path);
        Ok(())
    }

    pub fn close_port(&mut self) -> Result<(), String> {
        if self.port.is_some() {
            self.port = None;
            log::info!("串口已关闭");
        }
        Ok(())
    }

    pub fn send_command(&mut self, cmd: &str) -> Result<String, String> {
        let port = self.port.as_mut().ok_or("串口未打开")?;

        let cmd_bytes = format!("{}\r", cmd);
        port.write_all(cmd_bytes.as_bytes())
            .map_err(|e| format!("发送失败: {}", e))?;

        let mut buffer = Vec::new();
        let mut single_byte = [0u8; 1];
        let mut timeout_count = 0;
        let max_timeouts = 100;

        loop {
            match port.read(&mut single_byte) {
                Ok(0) => {
                    timeout_count += 1;
                    if timeout_count >= max_timeouts {
                        break;
                    }
                    continue;
                }
                Ok(_) => {
                    timeout_count = 0;
                    if single_byte[0] == b'\r' {
                        break;
                    }
                    buffer.push(single_byte[0]);
                }
                Err(ref e) if e.kind() == std::io::ErrorKind::TimedOut => {
                    timeout_count += 1;
                    if timeout_count >= max_timeouts {
                        break;
                    }
                    continue;
                }
                Err(e) => {
                    return Err(format!("读取失败: {}", e));
                }
            }
        }

        let response = String::from_utf8_lossy(&buffer).to_string();
        log::debug!("命令 {} → {}", cmd, response);
        Ok(response)
    }

    pub fn measure_once(&mut self) -> Result<(f64, f64, f64), String> {
        let response = self.send_command("MES,1")?;

        if !response.starts_with("OK00") {
            return Err(format!("测量失败: {}", response));
        }

        let parts: Vec<&str> = response.split(',').collect();
        if parts.len() < 6 {
            return Err(format!("响应格式错误: {}", response));
        }

        let x: f64 = parts[3].parse().map_err(|_| "x 解析失败")?;
        let y: f64 = parts[4].parse().map_err(|_| "y 解析失败")?;
        let lv: f64 = parts[5].parse().map_err(|_| "Lv 解析失败")?;

        Ok((x, y, lv))
    }
}

impl Default for SerialManager {
    fn default() -> Self {
        Self::new()
    }
}

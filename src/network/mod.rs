struct NetworkConfig {
    max_connections: u32,
    timeout_ms: u32,
    retry_attempts: u8,
    server_address: String,
}

pub fn disconnect_server() {
    println!("Disconnected from server");
}

pub fn connect_server() -> &'static str {
    "Connection successful"
}

impl Default for NetworkConfig {
    fn default() -> Self {
        NetworkConfig {
            max_connections: 50,
            timeout_ms: 5000,
            retry_attempts: 3,
            server_address: String::from("localhost:8080"),
        }
    }
}
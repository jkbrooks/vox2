pub struct DatabaseConfig {
    pub host: String,
    pub port: u16,
    pub username: String,
    pub password: String,
    pub database_name: String,
}pub struct DatabaseConnection {
    config: DatabaseConfig,
}

impl DatabaseConnection {
    pub fn new(config: DatabaseConfig) -> Self {
        DatabaseConnection { config }
    }

    pub fn connect(&self) {
        // Connection logic here
    }

    pub fn disconnect(&self) {
        // Disconnection logic here
    }
}
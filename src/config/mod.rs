pub struct GameConfig {
    pub max_players: u32,
    pub world_size: f32,
    pub debug_mode: bool,
    pub server_port: u16,
}

impl Default for GameConfig {
    fn default() -> Self {
        GameConfig {
            max_players: 100,
            world_size: 1000.0,
            debug_mode: false,
            server_port: 8080,
        }
    }
}pub fn load_config() -> GameConfig {
    GameConfig::default()
}pub fn save_config(config: &GameConfig) {
    println!("Config: {{:?}}", config);
}#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_load_config() {
        let config = load_config();
        assert_eq!(config.max_players, 100);
    }

    #[test]
    fn test_save_config() {
        let config = load_config();
        save_config(&config);
    }
}
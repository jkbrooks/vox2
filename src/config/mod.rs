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
}
pub struct GameConfig {
    pub window_width: u32,
    pub window_height: u32,
    pub fullscreen: bool,
    pub vsync: bool,
}

pub fn load_config() -> GameConfig {
    GameConfig {
        window_width: 800,
        window_height: 600,
        fullscreen: false,
        vsync: true,
    }
}
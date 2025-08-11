pub enum AudioFormat {
    MP3,
    WAV,
    OGG,
}pub fn play_sound(sound_name: &str, format: AudioFormat) {
    println!("Playing sound {} with format {:?}", sound_name, format);
}pub fn get_sound_duration(sound_name: &str) -> u32 {
    sound_name.len() as u32 * 100
}#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_play_sound() {
        play_sound("test_sound", AudioFormat::MP3);
    }

    #[test]
    fn test_get_sound_duration() {
        assert_eq!(get_sound_duration("test_sound"), 1000);
    }
}
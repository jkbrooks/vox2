/// Audio utility module for the Vox2 game engine

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum AudioFormat {
    MP3,
    WAV,
    OGG,
}

impl std::fmt::Display for AudioFormat {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            AudioFormat::MP3 => write!(f, "MP3"),
            AudioFormat::WAV => write!(f, "WAV"),
            AudioFormat::OGG => write!(f, "OGG"),
        }
    }
}

/// Play a sound with the specified format
pub fn play_sound(sound_name: &str, format: AudioFormat) {
    println!("Playing sound [{}] with format [{}]", sound_name, format);
}

/// Get the duration of a sound based on its name
pub fn get_sound_duration(sound_name: &str) -> u32 {
    sound_name.len() as u32 * 100
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_play_sound() {
        // This test just ensures the function can be called without panicking
        play_sound("test_sound", AudioFormat::MP3);
        play_sound("another_sound", AudioFormat::WAV);
        play_sound("third_sound", AudioFormat::OGG);
    }

    #[test]
    fn test_get_sound_duration() {
        assert_eq!(get_sound_duration("test"), 400);
        assert_eq!(get_sound_duration("hello"), 500);
        assert_eq!(get_sound_duration(""), 0);
    }

    #[test]
    fn test_audio_format_display() {
        assert_eq!(format!("{}", AudioFormat::MP3), "MP3");
        assert_eq!(format!("{}", AudioFormat::WAV), "WAV");
        assert_eq!(format!("{}", AudioFormat::OGG), "OGG");
    }
}

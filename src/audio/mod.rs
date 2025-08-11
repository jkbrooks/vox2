pub enum AudioFormat {
    MP3,
    WAV,
    OGG,
}pub fn play_sound(sound_name: &str, format: AudioFormat) {
    println!("Playing sound {} with format {:?}", sound_name, format);
}
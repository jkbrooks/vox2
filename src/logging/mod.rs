pub mod logger {
    use std::fs::OpenOptions;
    use std::io::Write;

    pub fn log(message: &str) {
        let mut file = OpenOptions::new()
            .append(true)
            .create(true)
            .open("log.txt")
            .unwrap();
        writeln!(file, "{}", message).unwrap();
    }
}
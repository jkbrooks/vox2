pub fn validate_username(name: &str) -> bool {
    let len = name.len();
    len >= 3 && len <= 20 && name.chars().all(|c| c.is_alphanumeric() || c == '_')
}

pub fn validate_coordinates(x: f32, y: f32, z: f32) -> bool {
    x >= -1000.0 && x <= 1000.0 && y >= -1000.0 && y <= 1000.0 && z >= -1000.0 && z <= 1000.0
}

pub fn validate_color_hex(hex: &str) -> bool {
    hex.len() == 7 && hex.starts_with('#') && hex[1..].chars().all(|c| c.is_digit(16))
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn test_validate_username() {
        assert!(validate_username("valid_username"));
        assert!(!validate_username("ab"));
        assert!(!validate_username("invalid username"));
    }
    #[test]
    fn test_validate_coordinates() {
        assert!(validate_coordinates(0.0, 0.0, 0.0));
        assert!(!validate_coordinates(1001.0, 0.0, 0.0));
    }
    #[test]
    fn test_validate_color_hex() {
        assert!(validate_color_hex("#FFFFFF"));
        assert!(!validate_color_hex("#ZZZZZZ"));
    }
}
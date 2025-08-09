# Test for HHMMSS-first naming
import os

# Function to verify file naming

def test_file_naming():
    files = os.listdir('.');
    for file in files:
        assert file.startswith('HHMMSS'), f'File {file} does not start with HHMMSS'

if __name__ == '__main__':
    test_file_naming()
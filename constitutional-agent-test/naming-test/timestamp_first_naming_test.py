# Test for timestamp-first naming convention
import datetime

# Function to generate timestamp-first filename

def generate_filename():
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    return f'{timestamp}_test_file.txt'

# Example usage
if __name__ == '__main__':
    print(generate_filename())
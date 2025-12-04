import os
from scanner import ScanConfig, scan_file_for_secrets

TEST_DIR = "./tmp_debug_repo"
os.makedirs(TEST_DIR, exist_ok=True)

sample = '''# Sample Spring Boot properties
spring.datasource.url=jdbc:postgresql://db.example.com:5432/mydb
spring.datasource.username=app_user
spring.datasource.password=Sup3rS3cret!
app.api.key=abcd1234
service.client_secret=verylongsecretstring1234567890
some.other.token=eyJhbGc...fakejwt...
# a short token shouldn't be missed
short_api_key=ABCD1234
'''

file_path = os.path.join(TEST_DIR, 'application.properties')
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(sample)

config = ScanConfig(redact_secrets=True, include_line_numbers=True)
findings = scan_file_for_secrets(file_path, TEST_DIR, config)

print(f"Scanned file: {file_path}\nFindings: {len(findings)}\n")
for f in findings:
    print('-', f.secret_type, f"line={f.line_number}", f.file_path)
    print('  ', f.context)

# Cleanup guidance
print('\nTo re-run, inspect the file at', file_path)

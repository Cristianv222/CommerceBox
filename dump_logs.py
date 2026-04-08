import subprocess

try:
    result = subprocess.run(['docker', 'logs', '--tail', '150', 'commercebox_celery'], capture_output=True, text=True, encoding='utf-8')
    with open('c:\\GitHub\\GitHub\\CommerceBox\\celery_logs_clean.txt', 'w', encoding='utf-8') as f:
        f.write(result.stdout)
        f.write(result.stderr)
    print("Logs written to celery_logs_clean.txt")
except Exception as e:
    print("Error:", e)

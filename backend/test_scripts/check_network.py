import socket
import ssl

def check_port(host, port):
    print(f"Testing connectivity to {host}:{port}...")
    try:
        sock = socket.create_connection((host, port), timeout=5)
        print(f"✅ Connection to {host}:{port} SUCCEEDED!")
        sock.close()
        return True
    except Exception as e:
        print(f"❌ Connection to {host}:{port} FAILED: {e}")
        return False

print("--- DIAGNOSTIC: Checking Gmail SMTP Access ---")
print("This test checks if your network/antivirus is blocking email connections.\n")

access_587 = check_port("smtp.gmail.com", 587)
access_465 = check_port("smtp.gmail.com", 465)

print("\n--- RESULT ---")
if not access_587 and not access_465:
    print("BLOCKED: Your computer or network is completely blocking email connections.")
    print("Likely causes: Antivirus (Avast/McAfee) 'Mail Shield', or Corporate Firewall.")
elif access_587:
    print("OPEN: Port 587 is open. We should use this.")
elif access_465:
    print("OPEN: Port 465 is open. We should use this.")

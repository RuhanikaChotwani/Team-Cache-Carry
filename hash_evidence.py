import hashlib

def calculate_hash(file_path):
    sha256 = hashlib.sha256()

    with open(file_path, "rb") as file:
        while True:
            data = file.read(4096)
            if not data:
                break
            sha256.update(data)

    return sha256.hexdigest()


# Calculate hashes
original_hash = calculate_hash("evidence.jpg")
tampered_hash = calculate_hash("tampered_evidence.jpg")

print("\nIBVAP - EVIDENCE INTEGRITY CHECK")
print("------------------------------------------")
print("Original Hash:", original_hash)
print("Current Hash: ", tampered_hash)

# Compare hashes
if original_hash == tampered_hash:
    print("\n[VERIFIED] EVIDENCE VERIFIED - No tampering detected.")
else:
    print("\n[ALERT] TAMPERING DETECTED - Evidence has been modified!")
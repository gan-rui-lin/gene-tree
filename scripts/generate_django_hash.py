import argparse
import base64
import hashlib


def django_pbkdf2_sha256(password: str, salt: str, iterations: int = 720000) -> str:
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations,
    )
    encoded = base64.b64encode(digest).decode("ascii").strip()
    return f"pbkdf2_sha256${iterations}${salt}${encoded}"


def main():
    parser = argparse.ArgumentParser(description="Generate Django PBKDF2-SHA256 hash.")
    parser.add_argument("password", help="Plain text password")
    parser.add_argument("salt", help="Salt string")
    parser.add_argument(
        "--iterations", type=int, default=720000, help="PBKDF2 iterations"
    )
    args = parser.parse_args()

    print(django_pbkdf2_sha256(args.password, args.salt, args.iterations))


if __name__ == "__main__":
    main()

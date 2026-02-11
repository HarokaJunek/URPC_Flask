# generate_hash.py - Утилита для генерации хеша пароля
from werkzeug.security import generate_password_hash


def main():
    """Генерирует хеш пароля для вставки в БД"""
    print("🔐 Генератор хешей паролей")
    print("=" * 50)

    password = input("Введите пароль для хеширования: ").strip()

    if not password:
        print("❌ Пароль не может быть пустым!")
        return

    # Генерируем хеш
    hashed = generate_password_hash(password)

    print("\n✅ Результат:")
    print(f"Пароль: {password}")
    print(f"Хеш: {hashed}")


if __name__ == "__main__":
    main()
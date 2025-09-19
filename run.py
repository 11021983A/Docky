#!/usr/bin/env python3
"""
Упрощенный скрипт запуска бота для Render
Решает проблемы с конфликтами процессов
"""

import os
import sys
import time
import subprocess
import signal

def kill_old_processes():
    """Убивает старые процессы Python"""
    try:
        # Находим и убиваем старые процессы bot.py
        result = subprocess.run(['pkill', '-f', 'bot.py'], capture_output=True)
        if result.returncode == 0:
            print("✅ Старые процессы остановлены")
            time.sleep(2)
    except Exception as e:
        print(f"⚠️ Не удалось остановить старые процессы: {e}")

def main():
    """Основная функция запуска"""
    print("=" * 50)
    print("🚀 ЗАПУСК БОТА ДОКИ")
    print("=" * 50)
    
    # Убиваем старые процессы
    kill_old_processes()
    
    # Ждем немного
    time.sleep(3)
    
    # Запускаем основной скрипт
    print("▶️ Запускаем bot.py...")
    
    try:
        # Запускаем bot.py как подпроцесс
        process = subprocess.Popen(
            [sys.executable, 'bot.py'],
            stdout=sys.stdout,
            stderr=sys.stderr
        )
        
        # Ждем завершения
        process.wait()
        
    except KeyboardInterrupt:
        print("\n⏹️ Остановка бота...")
        process.terminate()
        time.sleep(2)
        process.kill()
        sys.exit(0)
    except Exception as e:
        print(f"❌ Ошибка запуска: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

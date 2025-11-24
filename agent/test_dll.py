"""
TC-200 DLL接続テスト
このファイルを実行してDLLが正しく読み込めるか確認します
"""

import ctypes
import os
import sys

def test_dll_loading():
    """DLLの読み込みテスト"""

    # DLLファイルのパスを設定（実際のパスに変更してください）
    dll_paths = [
        "TC-200.dll",                              # 同じフォルダ
        r"C:\Program Files\TechCore\TC-200\TC-200.dll",  # インストール先（例）
        r"C:\TC-200\TC-200.dll",                   # 別の可能性
    ]

    dll_loaded = False

    for dll_path in dll_paths:
        print(f"\n📁 試行中: {dll_path}")

        if os.path.exists(dll_path):
            print(f"  ✅ ファイル存在確認")

            try:
                dll = ctypes.CDLL(dll_path)
                print(f"  ✅ DLL読み込み成功！")
                dll_loaded = True

                # DLL内の関数一覧を取得してみる（可能な場合）
                print("\n📋 利用可能な関数を探索中...")

                # よくある関数名を試す
                common_functions = [
                    "Initialize",
                    "GetVersion",
                    "GetSerialNumber",
                    "Open",
                    "Close",
                    "GetStatus",
                    "Connect",
                    "Disconnect"
                ]

                for func_name in common_functions:
                    try:
                        func = getattr(dll, func_name)
                        print(f"  ✅ 関数発見: {func_name}")
                    except AttributeError:
                        pass

                return dll

            except Exception as e:
                print(f"  ❌ 読み込みエラー: {e}")
        else:
            print(f"  ❌ ファイルが見つかりません")

    if not dll_loaded:
        print("\n❌ DLLを読み込めませんでした")
        print("\n💡 解決方法:")
        print("1. TC-200.dllファイルの場所を確認してください")
        print("2. このスクリプトと同じフォルダにDLLをコピーしてください")
        print("3. または、正しいパスをdll_pathsリストに追加してください")

    return None

def test_basic_functions(dll):
    """基本的な関数のテスト"""
    if not dll:
        return

    print("\n🔧 基本関数テスト")

    # バージョン取得を試す（例）
    try:
        # 多くのDLLはバージョン取得関数を持っている
        version_buffer = ctypes.create_string_buffer(100)
        result = dll.GetVersion(version_buffer)

        if result == 0:  # 通常、0は成功を意味する
            version = version_buffer.value.decode('utf-8')
            print(f"  ✅ バージョン: {version}")
        else:
            print(f"  ⚠️ バージョン取得失敗 (エラーコード: {result})")
    except Exception as e:
        print(f"  ℹ️ GetVersion関数なし: {e}")

    # シリアル番号取得を試す（例）
    try:
        serial_buffer = ctypes.create_string_buffer(50)
        result = dll.GetSerialNumber(serial_buffer)

        if result == 0:
            serial = serial_buffer.value.decode('utf-8')
            print(f"  ✅ シリアル番号: {serial}")
        else:
            print(f"  ⚠️ シリアル番号取得失敗 (エラーコード: {result})")
    except Exception as e:
        print(f"  ℹ️ GetSerialNumber関数なし: {e}")

if __name__ == "__main__":
    print("=" * 50)
    print("TC-200 DLL 接続テスト")
    print("=" * 50)

    # Python バージョン確認
    print(f"\n🐍 Python バージョン: {sys.version}")
    print(f"📂 実行フォルダ: {os.getcwd()}")

    # DLL読み込みテスト
    dll = test_dll_loading()

    # 基本関数テスト
    if dll:
        test_basic_functions(dll)
        print("\n✅ テスト完了！")
        print("\n次のステップ:")
        print("1. DLLの仕様書を確認して、正確な関数名と引数を把握する")
        print("2. terminal_controller.pyを作成して、実際の制御クラスを実装する")

    input("\n[Enterキーで終了]")
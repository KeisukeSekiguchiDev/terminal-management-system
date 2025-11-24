# エージェント実装仕様書
## 店舗PC用TMSエージェント

**文書バージョン**: 1.0
**作成日**: 2025年11月24日
**対象端末**: TC-200（USB接続カードリーダー）

---

## 1. エージェント概要

### 1.1 アーキテクチャ

```
┌────────────────────────────────────────┐
│            店舗PC（Windows）             │
│                                        │
│  ┌──────────────────────────────────┐ │
│  │      TMSエージェント (Python)      │ │
│  │                                   │ │
│  │  ┌─────────────┐ ┌─────────────┐│ │
│  │  │  Main Loop  │ │  API Client  ││ │
│  │  └──────┬──────┘ └───────┬──────┘│ │
│  │         │                 │       │ │
│  │  ┌──────┴──────┐ ┌───────┴──────┐│ │
│  │  │ USB Monitor │ │ Heartbeat    ││ │
│  │  └──────┬──────┘ └───────┬──────┘│ │
│  │         │                 │       │ │
│  │  ┌──────┴──────────────────┴──────┐│ │
│  │  │   TC-200 Controller (DLL)      ││ │
│  │  └──────────────┬──────────────────┘│ │
│  └─────────────────┼────────────────────┘ │
│                    │                      │
│         ┌──────────┴──────────┐          │
│         │  TC-200.dll         │          │
│         └──────────┬──────────┘          │
│                    │                      │
│         ┌──────────┴──────────┐          │
│         │  TC-200 Terminal    │          │
│         │  (USB Connection)   │          │
│         └─────────────────────┘          │
└────────────────────────────────────────┘
```

### 1.2 主要機能

| 機能 | 説明 | 実行頻度 |
|------|------|----------|
| ハートビート送信 | サーバーへの生存通知 | 5分ごと |
| 端末状態監視 | USB接続状態チェック | 30秒ごと |
| メトリクス収集 | CPU/メモリ使用率 | 5分ごと |
| ファームウェア更新 | リモート更新実行 | オンデマンド |
| ログ送信 | エラーログアップロード | 発生時 |
| 自動復旧 | 接続エラー時の再接続 | エラー検知時 |

---

## 2. ディレクトリ構造

```
agent/
├── main.py                 # メインエントリーポイント
├── config.py              # 設定管理
├── terminal_controller.py  # TC-200制御
├── api_client.py          # API通信
├── monitoring.py          # システム監視
├── updater.py            # 自動更新機能
├── logger.py             # ログ管理
├── utils.py              # ユーティリティ
├── requirements.txt       # 依存パッケージ
├── config.ini            # 設定ファイル
├── install.py            # インストーラー
├── service.py            # Windowsサービス
└── dll/
    └── TC-200.dll        # 端末制御DLL
```

---

## 3. 詳細実装

### 3.1 メインプログラム (main.py)

```python
# agent/main.py

import sys
import time
import signal
import logging
import threading
from datetime import datetime
from config import Config
from terminal_controller import TerminalController
from api_client import APIClient
from monitoring import SystemMonitor
from updater import AutoUpdater

class TMSAgent:
    """TMSエージェントのメインクラス"""

    def __init__(self):
        """初期化"""
        # 設定読み込み
        self.config = Config('config.ini')

        # ロガー初期化
        self.setup_logging()
        self.logger = logging.getLogger(__name__)

        # コンポーネント初期化
        self.terminal = TerminalController(self.config.dll_path)
        self.api = APIClient(
            self.config.server_url,
            self.config.api_key
        )
        self.monitor = SystemMonitor()
        self.updater = AutoUpdater(self.config)

        # 実行フラグ
        self.running = False
        self.threads = []

        # シグナルハンドラー設定
        signal.signal(signal.SIGINT, self.shutdown)
        signal.signal(signal.SIGTERM, self.shutdown)

    def setup_logging(self):
        """ログ設定"""
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        log_file = f'logs/agent_{datetime.now():%Y%m%d}.log'

        logging.basicConfig(
            level=logging.INFO,
            format=log_format,
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )

    def start(self):
        """エージェント起動"""
        self.logger.info("TMSエージェントを起動します")
        self.running = True

        # 端末接続確認
        if not self.check_terminal_connection():
            self.logger.error("TC-200端末が検出できません")
            return False

        # 初回登録
        if not self.register_agent():
            self.logger.error("サーバー登録に失敗しました")
            return False

        # 監視スレッド起動
        self.start_monitoring_threads()

        # メインループ
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            pass

        self.shutdown()
        return True

    def check_terminal_connection(self):
        """端末接続確認"""
        try:
            # USB接続チェック
            if not self.terminal.is_connected():
                self.logger.warning("端末が接続されていません")

                # 自動検出試行
                self.logger.info("端末を検索中...")
                devices = self.terminal.scan_devices()

                if devices:
                    # 最初のデバイスに接続
                    if self.terminal.connect(devices[0]):
                        self.logger.info(f"端末に接続しました: {devices[0]}")
                        return True

                return False

            # 端末情報取得
            info = self.terminal.get_device_info()
            self.logger.info(f"端末検出: {info['serial_number']}")

            return True

        except Exception as e:
            self.logger.error(f"端末接続エラー: {e}")
            return False

    def register_agent(self):
        """サーバー登録"""
        try:
            # 端末情報収集
            terminal_info = self.terminal.get_device_info()
            system_info = self.monitor.get_system_info()

            # 登録データ作成
            registration_data = {
                "serial_number": terminal_info['serial_number'],
                "firmware_version": terminal_info['firmware_version'],
                "agent_version": self.config.agent_version,
                "hostname": system_info['hostname'],
                "os_version": system_info['os_version'],
                "ip_address": system_info['ip_address']
            }

            # サーバー登録
            response = self.api.register(registration_data)

            if response['status'] == 'success':
                self.logger.info("サーバー登録完了")
                # トークン保存
                self.config.save_token(response['token'])
                return True

            return False

        except Exception as e:
            self.logger.error(f"登録エラー: {e}")
            return False

    def start_monitoring_threads(self):
        """監視スレッド起動"""
        # ハートビートスレッド
        heartbeat_thread = threading.Thread(
            target=self.heartbeat_loop,
            daemon=True
        )
        heartbeat_thread.start()
        self.threads.append(heartbeat_thread)

        # 端末監視スレッド
        terminal_thread = threading.Thread(
            target=self.terminal_monitor_loop,
            daemon=True
        )
        terminal_thread.start()
        self.threads.append(terminal_thread)

        # 更新チェックスレッド
        update_thread = threading.Thread(
            target=self.update_check_loop,
            daemon=True
        )
        update_thread.start()
        self.threads.append(update_thread)

        self.logger.info("監視スレッドを起動しました")

    def heartbeat_loop(self):
        """ハートビート送信ループ"""
        while self.running:
            try:
                # メトリクス収集
                metrics = self.monitor.get_metrics()
                terminal_status = self.terminal.get_status()

                # ハートビートデータ
                heartbeat_data = {
                    "serial_number": self.terminal.serial_number,
                    "status": "online" if terminal_status['connected'] else "offline",
                    "timestamp": datetime.now().isoformat(),
                    "metrics": {
                        "cpu_usage": metrics['cpu_usage'],
                        "memory_usage": metrics['memory_usage'],
                        "disk_usage": metrics['disk_usage'],
                        "uptime": metrics['uptime']
                    },
                    "terminal": {
                        "firmware_version": terminal_status['firmware_version'],
                        "transaction_count": terminal_status['transaction_count'],
                        "last_transaction": terminal_status['last_transaction']
                    }
                }

                # サーバー送信
                response = self.api.send_heartbeat(heartbeat_data)

                # コマンド処理
                if 'commands' in response:
                    self.process_commands(response['commands'])

                self.logger.debug("ハートビート送信完了")

            except Exception as e:
                self.logger.error(f"ハートビートエラー: {e}")

            # 5分待機
            time.sleep(300)

    def terminal_monitor_loop(self):
        """端末監視ループ"""
        error_count = 0
        max_errors = 5

        while self.running:
            try:
                # USB接続状態確認
                if not self.terminal.is_connected():
                    self.logger.warning("端末との接続が切断されました")

                    # 再接続試行
                    if self.terminal.reconnect():
                        self.logger.info("端末に再接続しました")
                        error_count = 0

                        # 切断イベント通知
                        self.api.send_event({
                            "type": "reconnected",
                            "serial_number": self.terminal.serial_number,
                            "timestamp": datetime.now().isoformat()
                        })
                    else:
                        error_count += 1

                        if error_count >= max_errors:
                            # エラーアラート送信
                            self.api.send_alert({
                                "type": "connection_lost",
                                "serial_number": self.terminal.serial_number,
                                "message": "端末との接続が回復しません",
                                "timestamp": datetime.now().isoformat()
                            })

                            # エラーカウントリセット（次回再試行のため）
                            error_count = 0
                else:
                    # 端末状態チェック
                    status = self.terminal.get_detailed_status()

                    # エラー検出
                    if status['has_error']:
                        self.logger.error(f"端末エラー: {status['error_code']}")

                        # エラー通知
                        self.api.send_alert({
                            "type": "terminal_error",
                            "serial_number": self.terminal.serial_number,
                            "error_code": status['error_code'],
                            "error_message": status['error_message'],
                            "timestamp": datetime.now().isoformat()
                        })

            except Exception as e:
                self.logger.error(f"端末監視エラー: {e}")

            # 30秒待機
            time.sleep(30)

    def update_check_loop(self):
        """更新チェックループ"""
        while self.running:
            try:
                # エージェント更新チェック
                if self.updater.check_agent_update():
                    self.logger.info("エージェント更新が利用可能です")

                    # 自動更新実行
                    if self.config.auto_update_enabled:
                        self.perform_agent_update()

                # ファームウェア更新チェック
                firmware_update = self.api.check_firmware_update(
                    self.terminal.serial_number
                )

                if firmware_update:
                    self.logger.info(f"ファームウェア更新: {firmware_update['version']}")
                    self.perform_firmware_update(firmware_update)

            except Exception as e:
                self.logger.error(f"更新チェックエラー: {e}")

            # 1時間待機
            time.sleep(3600)

    def process_commands(self, commands):
        """リモートコマンド処理"""
        for command in commands:
            try:
                self.logger.info(f"コマンド実行: {command['type']}")

                if command['type'] == 'restart':
                    self.restart_terminal()

                elif command['type'] == 'update_firmware':
                    self.perform_firmware_update(command['params'])

                elif command['type'] == 'collect_logs':
                    self.send_logs()

                elif command['type'] == 'run_diagnostic':
                    self.run_diagnostics()

                elif command['type'] == 'update_config':
                    self.update_configuration(command['params'])

                else:
                    self.logger.warning(f"不明なコマンド: {command['type']}")

                # コマンド完了通知
                self.api.send_command_result({
                    "command_id": command['id'],
                    "status": "completed",
                    "timestamp": datetime.now().isoformat()
                })

            except Exception as e:
                self.logger.error(f"コマンド実行エラー: {e}")

                # エラー通知
                self.api.send_command_result({
                    "command_id": command['id'],
                    "status": "failed",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                })

    def restart_terminal(self):
        """端末再起動"""
        self.logger.info("端末を再起動します")

        # 端末リセット
        self.terminal.reset()
        time.sleep(5)

        # 再接続
        self.terminal.reconnect()

    def perform_firmware_update(self, update_info):
        """ファームウェア更新実行"""
        try:
            self.logger.info(f"ファームウェア更新開始: {update_info['version']}")

            # ファームウェアダウンロード
            firmware_file = self.api.download_firmware(
                update_info['download_url']
            )

            # 更新実行
            result = self.terminal.update_firmware(firmware_file)

            if result['success']:
                self.logger.info("ファームウェア更新完了")

                # 成功通知
                self.api.send_update_result({
                    "serial_number": self.terminal.serial_number,
                    "version": update_info['version'],
                    "status": "success",
                    "timestamp": datetime.now().isoformat()
                })
            else:
                raise Exception(result['error'])

        except Exception as e:
            self.logger.error(f"ファームウェア更新失敗: {e}")

            # 失敗通知
            self.api.send_update_result({
                "serial_number": self.terminal.serial_number,
                "version": update_info['version'],
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })

    def perform_agent_update(self):
        """エージェント自己更新"""
        try:
            self.logger.info("エージェント更新を開始します")

            # 更新実行
            if self.updater.update():
                self.logger.info("エージェント更新完了、再起動します")

                # 再起動
                self.restart_agent()

        except Exception as e:
            self.logger.error(f"エージェント更新失敗: {e}")

    def send_logs(self):
        """ログ送信"""
        try:
            # ログファイル収集
            log_files = self.collect_log_files()

            # 圧縮
            archive = self.compress_logs(log_files)

            # アップロード
            self.api.upload_logs(archive)

            self.logger.info("ログ送信完了")

        except Exception as e:
            self.logger.error(f"ログ送信エラー: {e}")

    def run_diagnostics(self):
        """診断実行"""
        try:
            self.logger.info("診断を開始します")

            # 診断項目実行
            diagnostics = {
                "terminal_test": self.terminal.run_self_test(),
                "network_test": self.test_network_connectivity(),
                "system_check": self.monitor.run_system_check(),
                "timestamp": datetime.now().isoformat()
            }

            # 結果送信
            self.api.send_diagnostics(diagnostics)

            self.logger.info("診断完了")

        except Exception as e:
            self.logger.error(f"診断エラー: {e}")

    def shutdown(self, signum=None, frame=None):
        """シャットダウン処理"""
        self.logger.info("エージェントを停止します")
        self.running = False

        # スレッド停止待機
        for thread in self.threads:
            thread.join(timeout=5)

        # 切断通知
        try:
            self.api.send_event({
                "type": "agent_shutdown",
                "serial_number": self.terminal.serial_number,
                "timestamp": datetime.now().isoformat()
            })
        except:
            pass

        # リソースクリーンアップ
        self.terminal.disconnect()

        self.logger.info("エージェント停止完了")
        sys.exit(0)

    def restart_agent(self):
        """エージェント再起動"""
        import os
        import subprocess

        self.logger.info("エージェントを再起動します")

        # 新プロセス起動
        subprocess.Popen([sys.executable] + sys.argv)

        # 現プロセス終了
        self.shutdown()


def main():
    """メインエントリーポイント"""
    agent = TMSAgent()
    agent.start()


if __name__ == "__main__":
    main()
```

### 3.2 端末コントローラー (terminal_controller.py)

```python
# agent/terminal_controller.py

import ctypes
import time
import logging
from typing import Dict, List, Optional, Any

class TerminalController:
    """TC-200端末制御クラス"""

    def __init__(self, dll_path: str = "dll/TC-200.dll"):
        """
        初期化

        Args:
            dll_path: TC-200.dllのパス
        """
        self.logger = logging.getLogger(__name__)
        self.dll_path = dll_path
        self.dll = None
        self.serial_number = None
        self.connected = False

        # DLLロード
        self.load_dll()

    def load_dll(self):
        """DLLロード"""
        try:
            self.dll = ctypes.CDLL(self.dll_path)

            # 関数定義
            self.setup_dll_functions()

            self.logger.info(f"DLLロード完了: {self.dll_path}")

        except Exception as e:
            self.logger.error(f"DLLロードエラー: {e}")
            raise

    def setup_dll_functions(self):
        """DLL関数定義"""
        # 初期化
        self.dll.Initialize.argtypes = []
        self.dll.Initialize.restype = ctypes.c_int

        # デバイススキャン
        self.dll.ScanDevices.argtypes = [
            ctypes.POINTER(ctypes.c_char_p),
            ctypes.c_int
        ]
        self.dll.ScanDevices.restype = ctypes.c_int

        # 接続
        self.dll.Connect.argtypes = [ctypes.c_char_p]
        self.dll.Connect.restype = ctypes.c_int

        # 切断
        self.dll.Disconnect.argtypes = []
        self.dll.Disconnect.restype = ctypes.c_int

        # 状態取得
        self.dll.GetStatus.argtypes = [ctypes.POINTER(StatusInfo)]
        self.dll.GetStatus.restype = ctypes.c_int

        # デバイス情報取得
        self.dll.GetDeviceInfo.argtypes = [ctypes.POINTER(DeviceInfo)]
        self.dll.GetDeviceInfo.restype = ctypes.c_int

        # ファームウェア更新
        self.dll.UpdateFirmware.argtypes = [ctypes.c_char_p]
        self.dll.UpdateFirmware.restype = ctypes.c_int

        # セルフテスト
        self.dll.RunSelfTest.argtypes = []
        self.dll.RunSelfTest.restype = ctypes.c_int

        # リセット
        self.dll.Reset.argtypes = []
        self.dll.Reset.restype = ctypes.c_int

    def scan_devices(self) -> List[str]:
        """
        USB接続されているTC-200デバイスをスキャン

        Returns:
            検出されたデバイスのシリアル番号リスト
        """
        try:
            # バッファ準備
            max_devices = 10
            device_array = (ctypes.c_char_p * max_devices)()

            # スキャン実行
            count = self.dll.ScanDevices(device_array, max_devices)

            # 結果取得
            devices = []
            for i in range(count):
                if device_array[i]:
                    devices.append(device_array[i].decode('utf-8'))

            self.logger.info(f"{count}台のデバイスを検出")
            return devices

        except Exception as e:
            self.logger.error(f"デバイススキャンエラー: {e}")
            return []

    def connect(self, serial_number: str = None) -> bool:
        """
        端末に接続

        Args:
            serial_number: 接続するデバイスのシリアル番号

        Returns:
            接続成功の場合True
        """
        try:
            # 既に接続中の場合は切断
            if self.connected:
                self.disconnect()

            # シリアル番号が指定されていない場合は最初のデバイスに接続
            if not serial_number:
                devices = self.scan_devices()
                if not devices:
                    self.logger.error("接続可能なデバイスが見つかりません")
                    return False
                serial_number = devices[0]

            # 接続実行
            result = self.dll.Connect(serial_number.encode('utf-8'))

            if result == 0:
                self.serial_number = serial_number
                self.connected = True
                self.logger.info(f"端末に接続: {serial_number}")
                return True
            else:
                self.logger.error(f"接続失敗: エラーコード {result}")
                return False

        except Exception as e:
            self.logger.error(f"接続エラー: {e}")
            return False

    def disconnect(self):
        """端末との接続を切断"""
        try:
            if self.connected:
                self.dll.Disconnect()
                self.connected = False
                self.logger.info("端末との接続を切断")

        except Exception as e:
            self.logger.error(f"切断エラー: {e}")

    def is_connected(self) -> bool:
        """
        接続状態確認

        Returns:
            接続中の場合True
        """
        try:
            if not self.connected:
                return False

            # 実際の接続状態を確認
            status = StatusInfo()
            result = self.dll.GetStatus(ctypes.byref(status))

            if result != 0:
                self.connected = False
                return False

            return True

        except:
            self.connected = False
            return False

    def reconnect(self) -> bool:
        """
        再接続

        Returns:
            再接続成功の場合True
        """
        self.logger.info("再接続を試みます")

        # 一度切断
        self.disconnect()
        time.sleep(2)

        # 再接続
        return self.connect(self.serial_number)

    def get_device_info(self) -> Dict[str, Any]:
        """
        デバイス情報取得

        Returns:
            デバイス情報の辞書
        """
        try:
            info = DeviceInfo()
            result = self.dll.GetDeviceInfo(ctypes.byref(info))

            if result == 0:
                return {
                    "serial_number": info.serial_number.decode('utf-8'),
                    "firmware_version": info.firmware_version.decode('utf-8'),
                    "model": info.model.decode('utf-8'),
                    "manufacturer": "TechCore Solutions"
                }
            else:
                raise Exception(f"情報取得失敗: エラーコード {result}")

        except Exception as e:
            self.logger.error(f"デバイス情報取得エラー: {e}")
            return {}

    def get_status(self) -> Dict[str, Any]:
        """
        端末状態取得

        Returns:
            状態情報の辞書
        """
        try:
            status = StatusInfo()
            result = self.dll.GetStatus(ctypes.byref(status))

            if result == 0:
                return {
                    "connected": True,
                    "firmware_version": status.firmware_version.decode('utf-8'),
                    "transaction_count": status.transaction_count,
                    "last_transaction": status.last_transaction,
                    "error_code": status.error_code
                }
            else:
                return {
                    "connected": False,
                    "error": f"状態取得失敗: {result}"
                }

        except Exception as e:
            self.logger.error(f"状態取得エラー: {e}")
            return {"connected": False, "error": str(e)}

    def get_detailed_status(self) -> Dict[str, Any]:
        """
        詳細状態取得

        Returns:
            詳細状態情報
        """
        basic_status = self.get_status()

        # エラー判定
        has_error = basic_status.get('error_code', 0) != 0

        # エラーメッセージ取得
        error_message = ""
        if has_error:
            error_message = self.get_error_message(basic_status['error_code'])

        return {
            **basic_status,
            "has_error": has_error,
            "error_message": error_message
        }

    def get_error_message(self, error_code: int) -> str:
        """
        エラーコードからメッセージ取得

        Args:
            error_code: エラーコード

        Returns:
            エラーメッセージ
        """
        error_messages = {
            1: "通信エラー",
            2: "ハードウェアエラー",
            3: "ファームウェアエラー",
            4: "メモリエラー",
            5: "設定エラー",
            10: "カードリーダーエラー",
            11: "プリンターエラー",
            20: "温度異常",
            21: "電圧異常"
        }

        return error_messages.get(error_code, f"不明なエラー ({error_code})")

    def update_firmware(self, firmware_file: str) -> Dict[str, Any]:
        """
        ファームウェア更新

        Args:
            firmware_file: ファームウェアファイルパス

        Returns:
            更新結果
        """
        try:
            self.logger.info(f"ファームウェア更新開始: {firmware_file}")

            # 更新実行
            result = self.dll.UpdateFirmware(firmware_file.encode('utf-8'))

            if result == 0:
                self.logger.info("ファームウェア更新成功")

                # 再起動待機
                time.sleep(10)

                # 再接続
                self.reconnect()

                return {"success": True}
            else:
                error_msg = f"ファームウェア更新失敗: エラーコード {result}"
                self.logger.error(error_msg)
                return {"success": False, "error": error_msg}

        except Exception as e:
            error_msg = f"ファームウェア更新エラー: {e}"
            self.logger.error(error_msg)
            return {"success": False, "error": error_msg}

    def run_self_test(self) -> Dict[str, Any]:
        """
        セルフテスト実行

        Returns:
            テスト結果
        """
        try:
            self.logger.info("セルフテスト開始")

            result = self.dll.RunSelfTest()

            test_results = {
                "success": result == 0,
                "tests": {
                    "memory": (result & 0x01) == 0,
                    "communication": (result & 0x02) == 0,
                    "card_reader": (result & 0x04) == 0,
                    "printer": (result & 0x08) == 0,
                    "display": (result & 0x10) == 0,
                    "keypad": (result & 0x20) == 0
                }
            }

            self.logger.info(f"セルフテスト完了: {test_results}")
            return test_results

        except Exception as e:
            self.logger.error(f"セルフテストエラー: {e}")
            return {"success": False, "error": str(e)}

    def reset(self):
        """端末リセット"""
        try:
            self.logger.info("端末をリセットします")
            self.dll.Reset()

        except Exception as e:
            self.logger.error(f"リセットエラー: {e}")


# C構造体定義
class StatusInfo(ctypes.Structure):
    """状態情報構造体"""
    _fields_ = [
        ("firmware_version", ctypes.c_char * 20),
        ("transaction_count", ctypes.c_int),
        ("last_transaction", ctypes.c_int),
        ("error_code", ctypes.c_int)
    ]


class DeviceInfo(ctypes.Structure):
    """デバイス情報構造体"""
    _fields_ = [
        ("serial_number", ctypes.c_char * 50),
        ("firmware_version", ctypes.c_char * 20),
        ("model", ctypes.c_char * 30)
    ]
```

### 3.3 API クライアント (api_client.py)

```python
# agent/api_client.py

import json
import requests
import logging
from typing import Dict, Any, Optional
from urllib.parse import urljoin

class APIClient:
    """TMSサーバーAPIクライアント"""

    def __init__(self, server_url: str, api_key: str = None):
        """
        初期化

        Args:
            server_url: TMSサーバーURL
            api_key: APIキー
        """
        self.logger = logging.getLogger(__name__)
        self.server_url = server_url
        self.api_key = api_key
        self.token = None
        self.session = requests.Session()

        # デフォルトヘッダー設定
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'TMS-Agent/1.0'
        })

        if api_key:
            self.session.headers['X-API-Key'] = api_key

    def register(self, registration_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        エージェント登録

        Args:
            registration_data: 登録データ

        Returns:
            レスポンスデータ
        """
        url = urljoin(self.server_url, '/api/agent/register')

        try:
            response = self.session.post(url, json=registration_data)
            response.raise_for_status()

            data = response.json()

            # トークン保存
            if 'token' in data:
                self.token = data['token']
                self.session.headers['Authorization'] = f"Bearer {self.token}"

            return data

        except requests.exceptions.RequestException as e:
            self.logger.error(f"登録エラー: {e}")
            return {"status": "error", "message": str(e)}

    def send_heartbeat(self, heartbeat_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        ハートビート送信

        Args:
            heartbeat_data: ハートビートデータ

        Returns:
            レスポンスデータ（コマンド含む）
        """
        url = urljoin(self.server_url, '/api/heartbeat')

        try:
            response = self.session.post(url, json=heartbeat_data, timeout=30)
            response.raise_for_status()

            return response.json()

        except requests.exceptions.Timeout:
            self.logger.warning("ハートビートタイムアウト")
            return {}
        except requests.exceptions.RequestException as e:
            self.logger.error(f"ハートビートエラー: {e}")
            return {}

    def send_alert(self, alert_data: Dict[str, Any]) -> bool:
        """
        アラート送信

        Args:
            alert_data: アラートデータ

        Returns:
            送信成功の場合True
        """
        url = urljoin(self.server_url, '/api/alerts')

        try:
            response = self.session.post(url, json=alert_data)
            response.raise_for_status()
            return True

        except requests.exceptions.RequestException as e:
            self.logger.error(f"アラート送信エラー: {e}")
            return False

    def send_event(self, event_data: Dict[str, Any]) -> bool:
        """
        イベント送信

        Args:
            event_data: イベントデータ

        Returns:
            送信成功の場合True
        """
        url = urljoin(self.server_url, '/api/events')

        try:
            response = self.session.post(url, json=event_data)
            response.raise_for_status()
            return True

        except:
            return False

    def check_firmware_update(self, serial_number: str) -> Optional[Dict[str, Any]]:
        """
        ファームウェア更新チェック

        Args:
            serial_number: シリアル番号

        Returns:
            更新情報（更新がある場合）
        """
        url = urljoin(self.server_url, f'/api/firmware/check/{serial_number}')

        try:
            response = self.session.get(url)
            response.raise_for_status()

            data = response.json()

            if data.get('update_available'):
                return data['update_info']

            return None

        except requests.exceptions.RequestException as e:
            self.logger.error(f"更新チェックエラー: {e}")
            return None

    def download_firmware(self, download_url: str) -> str:
        """
        ファームウェアダウンロード

        Args:
            download_url: ダウンロードURL

        Returns:
            保存したファイルパス
        """
        import os
        import tempfile

        try:
            response = self.session.get(download_url, stream=True)
            response.raise_for_status()

            # 一時ファイルに保存
            fd, filepath = tempfile.mkstemp(suffix='.bin')

            with os.fdopen(fd, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            self.logger.info(f"ファームウェアダウンロード完了: {filepath}")
            return filepath

        except Exception as e:
            self.logger.error(f"ダウンロードエラー: {e}")
            raise

    def send_command_result(self, result_data: Dict[str, Any]) -> bool:
        """
        コマンド実行結果送信

        Args:
            result_data: 実行結果データ

        Returns:
            送信成功の場合True
        """
        url = urljoin(self.server_url, '/api/commands/result')

        try:
            response = self.session.post(url, json=result_data)
            response.raise_for_status()
            return True

        except:
            return False

    def send_update_result(self, result_data: Dict[str, Any]) -> bool:
        """
        更新結果送信

        Args:
            result_data: 更新結果データ

        Returns:
            送信成功の場合True
        """
        url = urljoin(self.server_url, '/api/firmware/result')

        try:
            response = self.session.post(url, json=result_data)
            response.raise_for_status()
            return True

        except:
            return False

    def upload_logs(self, log_archive: str) -> bool:
        """
        ログアップロード

        Args:
            log_archive: ログアーカイブファイルパス

        Returns:
            アップロード成功の場合True
        """
        url = urljoin(self.server_url, '/api/logs/upload')

        try:
            with open(log_archive, 'rb') as f:
                files = {'logs': f}
                response = self.session.post(url, files=files)
                response.raise_for_status()

            return True

        except Exception as e:
            self.logger.error(f"ログアップロードエラー: {e}")
            return False

    def send_diagnostics(self, diagnostics_data: Dict[str, Any]) -> bool:
        """
        診断結果送信

        Args:
            diagnostics_data: 診断結果データ

        Returns:
            送信成功の場合True
        """
        url = urljoin(self.server_url, '/api/diagnostics')

        try:
            response = self.session.post(url, json=diagnostics_data)
            response.raise_for_status()
            return True

        except:
            return False
```

---

## 4. 設定ファイル

### 4.1 設定ファイル (config.ini)

```ini
# agent/config.ini

[server]
# TMSサーバーURL
url = https://tms.techcore-solutions.jp

# APIキー（初回登録時に取得）
api_key =

# 認証トークン（自動設定）
token =

[agent]
# エージェントバージョン
version = 1.0.0

# 自動更新有効化
auto_update = true

# ログレベル (DEBUG, INFO, WARNING, ERROR)
log_level = INFO

# ログ保持日数
log_retention_days = 30

[terminal]
# DLLパス
dll_path = dll/TC-200.dll

# 再接続試行回数
reconnect_attempts = 5

# 再接続待機時間（秒）
reconnect_delay = 10

[monitoring]
# ハートビート間隔（秒）
heartbeat_interval = 300

# 端末監視間隔（秒）
terminal_check_interval = 30

# 更新チェック間隔（秒）
update_check_interval = 3600

[network]
# プロキシ設定
use_proxy = false
proxy_url =

# タイムアウト（秒）
timeout = 30

# リトライ回数
max_retries = 3
```

---

## 5. インストーラー

### 5.1 インストールスクリプト (install.py)

```python
# agent/install.py

import os
import sys
import shutil
import winreg
import logging
from pathlib import Path

class AgentInstaller:
    """TMSエージェントインストーラー"""

    def __init__(self):
        self.install_dir = Path(r"C:\Program Files\TechCore\TMS Agent")
        self.service_name = "TechCoreTMSAgent"
        self.logger = self.setup_logging()

    def setup_logging(self):
        """ログ設定"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        return logging.getLogger(__name__)

    def install(self):
        """インストール実行"""
        try:
            self.logger.info("TMSエージェントのインストールを開始します")

            # 管理者権限確認
            if not self.is_admin():
                self.logger.error("管理者権限で実行してください")
                return False

            # ディレクトリ作成
            self.create_directories()

            # ファイルコピー
            self.copy_files()

            # 依存パッケージインストール
            self.install_dependencies()

            # Windowsサービス登録
            self.register_service()

            # レジストリ設定
            self.setup_registry()

            # ファイアウォール例外追加
            self.setup_firewall()

            self.logger.info("インストール完了")
            return True

        except Exception as e:
            self.logger.error(f"インストールエラー: {e}")
            return False

    def is_admin(self):
        """管理者権限確認"""
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin()

    def create_directories(self):
        """ディレクトリ作成"""
        dirs = [
            self.install_dir,
            self.install_dir / "logs",
            self.install_dir / "dll",
            self.install_dir / "temp"
        ]

        for dir_path in dirs:
            dir_path.mkdir(parents=True, exist_ok=True)
            self.logger.info(f"ディレクトリ作成: {dir_path}")

    def copy_files(self):
        """ファイルコピー"""
        files = [
            "main.py",
            "config.py",
            "terminal_controller.py",
            "api_client.py",
            "monitoring.py",
            "updater.py",
            "logger.py",
            "utils.py",
            "config.ini",
            "requirements.txt",
            "service.py"
        ]

        for file in files:
            src = Path(file)
            dst = self.install_dir / file

            if src.exists():
                shutil.copy2(src, dst)
                self.logger.info(f"ファイルコピー: {file}")

        # DLLコピー
        dll_src = Path("dll/TC-200.dll")
        if dll_src.exists():
            shutil.copy2(dll_src, self.install_dir / "dll" / "TC-200.dll")

    def install_dependencies(self):
        """依存パッケージインストール"""
        import subprocess

        self.logger.info("依存パッケージをインストール中...")

        subprocess.check_call([
            sys.executable,
            "-m", "pip", "install",
            "-r", str(self.install_dir / "requirements.txt")
        ])

    def register_service(self):
        """Windowsサービス登録"""
        import subprocess

        service_path = self.install_dir / "service.py"

        # nssm使用（別途インストール必要）
        nssm_path = "nssm.exe"

        commands = [
            [nssm_path, "install", self.service_name, sys.executable, str(service_path)],
            [nssm_path, "set", self.service_name, "AppDirectory", str(self.install_dir)],
            [nssm_path, "set", self.service_name, "Description", "TechCore TMS Agent Service"],
            [nssm_path, "set", self.service_name, "Start", "SERVICE_AUTO_START"]
        ]

        for cmd in commands:
            subprocess.check_call(cmd)

        self.logger.info(f"サービス登録: {self.service_name}")

    def setup_registry(self):
        """レジストリ設定"""
        try:
            # アンインストール情報追加
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\TechCoreTMSAgent"

            with winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
                winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, "TechCore TMS Agent")
                winreg.SetValueEx(key, "DisplayVersion", 0, winreg.REG_SZ, "1.0.0")
                winreg.SetValueEx(key, "Publisher", 0, winreg.REG_SZ, "TechCore Solutions")
                winreg.SetValueEx(key, "InstallLocation", 0, winreg.REG_SZ, str(self.install_dir))
                winreg.SetValueEx(key, "UninstallString", 0, winreg.REG_SZ,
                                str(self.install_dir / "uninstall.exe"))

            self.logger.info("レジストリ設定完了")

        except Exception as e:
            self.logger.warning(f"レジストリ設定エラー: {e}")

    def setup_firewall(self):
        """ファイアウォール設定"""
        import subprocess

        try:
            # アウトバウンド通信許可
            subprocess.check_call([
                "netsh", "advfirewall", "firewall", "add", "rule",
                f"name=TechCore TMS Agent",
                "dir=out",
                "action=allow",
                f"program={self.install_dir / 'main.py'}"
            ])

            self.logger.info("ファイアウォール設定完了")

        except Exception as e:
            self.logger.warning(f"ファイアウォール設定エラー: {e}")

    def start_service(self):
        """サービス開始"""
        import subprocess

        try:
            subprocess.check_call(["net", "start", self.service_name])
            self.logger.info("サービスを開始しました")
        except:
            self.logger.warning("サービスの開始に失敗しました")


def main():
    """メイン処理"""
    installer = AgentInstaller()

    if installer.install():
        print("\n=== インストール完了 ===")
        print(f"インストール先: {installer.install_dir}")
        print(f"サービス名: {installer.service_name}")
        print("\nサービスを開始しますか？ (y/n): ", end="")

        if input().lower() == 'y':
            installer.start_service()
    else:
        print("\nインストールに失敗しました")
        sys.exit(1)


if __name__ == "__main__":
    main()
```

---

## まとめ

このエージェント実装仕様書により：

1. **店舗PCで自律的に動作**するエージェントプログラム
2. **USB接続のTC-200端末を制御**
3. **5分ごとにハートビート送信**
4. **異常検知時の自動アラート**
5. **リモートファームウェア更新対応**
6. **Windowsサービスとして常駐**

Devinがこの仕様書に基づいて完全に実装可能です。
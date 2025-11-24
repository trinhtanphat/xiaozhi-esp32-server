#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WebSocket性能测试工具
用于测试小智ESP32服务器的WebSocket连接性能
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
import requests
import json
import websocket
import threading
import time
from urllib.parse import quote
import psutil
from datetime import datetime
import queue


class WebSocketTestTool:
    def __init__(self, root):
        self.root = root
        self.root.title("WebSocket性能测试工具")
        self.root.geometry("1400x900")
        self.root.configure(bg="#f5f7fa")

        # 测试控制变量
        self.is_testing = False
        self.test_threads = []
        self.log_queue = queue.Queue()
        self.memory_data = []
        self.cpu_data = []

        # 创建主界面
        self.create_widgets()

        # 启动日志更新线程
        self.update_logs()

        # 启动内存监控线程
        self.start_memory_monitor()

    def create_widgets(self):
        # 顶部框架（连接信息 + 测试参数）
        top_frame = tk.Frame(self.root, bg="#f0f2f5")
        top_frame.pack(fill=tk.X, padx=20, pady=10)

        # 左侧：连接信息卡片
        self.create_connection_card(top_frame)

        # 右侧：测试参数卡片
        self.create_test_params_card(top_frame)

        # 中间：执行日志卡片
        self.create_log_card()

        # 底部：内存监控卡片
        self.create_memory_card()

    def create_connection_card(self, parent):
        """创建连接信息卡片"""
        card = tk.LabelFrame(
            parent,
            text="连接信息",
            bg="white",
            font=("Arial", 12, "bold"),
            padx=20,
            pady=15,
        )
        card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        # 设备MAC
        tk.Label(card, text="设备 MAC", bg="white", font=("Arial", 10)).grid(
            row=0, column=0, sticky=tk.W, pady=5
        )
        self.device_mac_entry = tk.Entry(card, font=("Arial", 10), width=40)
        self.device_mac_entry.grid(row=0, column=1, pady=5, padx=10)
        self.device_mac_entry.insert(0, "75:9E:6E:61:39:5A")

        # 客户端ID
        tk.Label(card, text="客户端 ID", bg="white", font=("Arial", 10)).grid(
            row=0, column=2, sticky=tk.W, pady=5
        )
        self.client_id_entry = tk.Entry(card, font=("Arial", 10), width=40)
        self.client_id_entry.grid(row=0, column=3, pady=5, padx=10)
        self.client_id_entry.insert(0, "web_test_client")

        # OTA地址
        tk.Label(card, text="OTA 地址", bg="white", font=("Arial", 10)).grid(
            row=1, column=0, sticky=tk.W, pady=5
        )
        self.ota_url_entry = tk.Entry(card, font=("Arial", 10), width=40)
        self.ota_url_entry.grid(row=1, column=1, pady=5, padx=10)
        self.ota_url_entry.insert(0, "http://localhost:8002/xiaozhi/ota/")

        # WebSocket地址（只读）
        tk.Label(card, text="WebSocket 地址", bg="white", font=("Arial", 10)).grid(
            row=1, column=2, sticky=tk.W, pady=5
        )
        self.ws_url_entry = tk.Entry(
            card, font=("Arial", 10), width=40, state="readonly", fg="gray"
        )
        self.ws_url_entry.grid(row=1, column=3, pady=5, padx=10)

    def create_test_params_card(self, parent):
        """创建测试参数卡片"""
        card = tk.LabelFrame(
            parent,
            text="测试参数",
            bg="white",
            font=("Arial", 12, "bold"),
            padx=20,
            pady=15,
        )
        card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 客户端数量
        tk.Label(card, text="客户端数量", bg="white", font=("Arial", 10)).grid(
            row=0, column=0, sticky=tk.W, pady=5
        )
        self.client_count_entry = tk.Entry(card, font=("Arial", 10), width=20)
        self.client_count_entry.grid(row=0, column=1, pady=5, padx=10)
        self.client_count_entry.insert(0, "10")

        # 连接持续时间
        tk.Label(card, text="持续时间 (秒)", bg="white", font=("Arial", 10)).grid(
            row=0, column=2, sticky=tk.W, pady=5
        )
        self.duration_entry = tk.Entry(card, font=("Arial", 10), width=20)
        self.duration_entry.grid(row=0, column=3, pady=5, padx=10)
        self.duration_entry.insert(0, "4")

        # 每轮次数
        tk.Label(card, text="每轮次数", bg="white", font=("Arial", 10)).grid(
            row=1, column=0, sticky=tk.W, pady=5
        )
        self.requests_per_round_entry = tk.Entry(card, font=("Arial", 10), width=20)
        self.requests_per_round_entry.grid(row=1, column=1, pady=5, padx=10)
        self.requests_per_round_entry.insert(0, "5")

        # 休息时间
        tk.Label(card, text="休息时间 (秒)", bg="white", font=("Arial", 10)).grid(
            row=1, column=2, sticky=tk.W, pady=5
        )
        self.rest_time_entry = tk.Entry(card, font=("Arial", 10), width=20)
        self.rest_time_entry.grid(row=1, column=3, pady=5, padx=10)
        self.rest_time_entry.insert(0, "5")

        # 按钮框架
        button_frame = tk.Frame(card, bg="white")
        button_frame.grid(row=2, column=0, columnspan=4, pady=15)

        # 开始测试按钮
        self.start_btn = tk.Button(
            button_frame,
            text="▶ 开始测试",
            bg="#4169E1",
            fg="white",
            font=("Arial", 11, "bold"),
            width=20,
            height=2,
            command=self.start_test,
            cursor="hand2",
        )
        self.start_btn.pack(side=tk.LEFT, padx=10)

        # 停止测试按钮
        self.stop_btn = tk.Button(
            button_frame,
            text="■ 停止测试",
            bg="#808080",
            fg="white",
            font=("Arial", 11, "bold"),
            width=20,
            height=2,
            command=self.stop_test,
            cursor="hand2",
            state=tk.DISABLED,
        )
        self.stop_btn.pack(side=tk.LEFT, padx=10)

    def create_log_card(self):
        """创建执行日志卡片"""
        card = tk.LabelFrame(
            self.root,
            text="执行日志",
            bg="white",
            font=("Arial", 12, "bold"),
            padx=10,
            pady=10,
        )
        card.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        # 创建滚动文本框
        self.log_text = scrolledtext.ScrolledText(
            card, font=("Consolas", 9), bg="#f8f9fa", height=15, wrap=tk.WORD
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # 配置日志颜色标签
        self.log_text.tag_config("INFO", foreground="black")
        self.log_text.tag_config("SUCCESS", foreground="green")
        self.log_text.tag_config("ERROR", foreground="red")
        self.log_text.tag_config("WARNING", foreground="orange")

    def create_memory_card(self):
        """创建内存监控卡片"""
        card = tk.LabelFrame(
            self.root,
            text="内存监控 (8000端口)",
            bg="white",
            font=("Arial", 12, "bold"),
            padx=10,
            pady=10,
        )
        card.pack(fill=tk.BOTH, padx=20, pady=(0, 20))

        # 创建Canvas容器框架
        canvas_frame = tk.Frame(card, bg="white")
        canvas_frame.pack(fill=tk.BOTH, expand=True)

        # 左侧Canvas - 完整趋势图
        left_frame = tk.Frame(canvas_frame, bg="white")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        tk.Label(
            left_frame, text="完整趋势 (最近100个数据点)", bg="white", font=("Arial", 9)
        ).pack()
        self.memory_canvas_full = tk.Canvas(left_frame, bg="white", height=180)
        self.memory_canvas_full.pack(fill=tk.BOTH, expand=True)

        # 右侧Canvas - 最近10个数据点放大视图
        right_frame = tk.Frame(canvas_frame, bg="white")
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))

        tk.Label(
            right_frame, text="近期详情 (最近10个数据点)", bg="white", font=("Arial", 9)
        ).pack()
        self.memory_canvas_recent = tk.Canvas(right_frame, bg="white", height=180)
        self.memory_canvas_recent.pack(fill=tk.BOTH, expand=True)

        # 内存和CPU信息标签
        self.memory_label = tk.Label(
            card, text="当前内存: -- MB | 峰值: -- MB | CPU: -- %", bg="white", font=("Arial", 10)
        )
        self.memory_label.pack(pady=5)

    def log(self, message, level="INFO"):
        """添加日志到队列"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_queue.put((timestamp, message, level))

    def update_logs(self):
        """定期更新日志显示"""
        try:
            while True:
                timestamp, message, level = self.log_queue.get_nowait()
                log_line = f"[{timestamp}] {message}\n"
                self.log_text.insert(tk.END, log_line, level)
                self.log_text.see(tk.END)
        except queue.Empty:
            pass

        # 每100ms更新一次
        self.root.after(100, self.update_logs)

    def get_websocket_url(self):
        """从OTA地址获取WebSocket URL"""
        try:
            ota_url = self.ota_url_entry.get().strip()
            device_mac = self.device_mac_entry.get().strip()
            client_id = self.client_id_entry.get().strip()

            headers = {
                "Client-Id": client_id,
                "Device-Id": device_mac,
                "Content-Type": "application/json",
            }

            payload = {
                "version": 0,
                "uuid": "",
                "application": {
                    "name": "xiaozhi-web-test",
                    "version": "1.0.0",
                    "compile_time": "2025-04-16 10:00:00",
                    "idf_version": "4.4.3",
                    "elf_sha256": "1234567890abcdef1234567890abcdef1234567890abcdef",
                },
                "ota": {"label": "xiaozhi-web-test"},
                "board": {
                    "type": "xiaozhi-web-test",
                    "ssid": "xiaozhi-web-test",
                    "rssi": 0,
                    "channel": 0,
                    "ip": "192.168.1.1",
                    "mac": device_mac,
                },
                "flash_size": 0,
                "minimum_free_heap_size": 0,
                "mac_address": device_mac,
                "chip_model_name": "",
                "chip_info": {"model": 0, "cores": 0, "revision": 0, "features": 0},
                "partition_table": [
                    {"label": "", "type": 0, "subtype": 0, "address": 0, "size": 0}
                ],
            }

            self.log(f"请求OTA地址: {ota_url}", "INFO")
            response = requests.post(ota_url, headers=headers, json=payload, timeout=10)

            if response.status_code == 200:
                data = response.json()
                ws_base_url = data.get("websocket", {}).get("url", "")

                if ws_base_url:
                    # URL编码设备MAC
                    encoded_mac = quote(device_mac)
                    ws_url = (
                        f"{ws_base_url}?device-id={encoded_mac}&client-id={client_id}"
                    )

                    # 更新WebSocket地址显示
                    self.ws_url_entry.config(state="normal")
                    self.ws_url_entry.delete(0, tk.END)
                    self.ws_url_entry.insert(0, ws_url)
                    self.ws_url_entry.config(state="readonly")

                    self.log(f"获取WebSocket地址成功: {ws_url}", "SUCCESS")
                    return ws_url
                else:
                    self.log("OTA响应中未找到WebSocket URL", "ERROR")
                    return None
            else:
                self.log(f"OTA请求失败，状态码: {response.status_code}", "ERROR")
                return None

        except Exception as e:
            self.log(f"获取WebSocket地址失败: {str(e)}", "ERROR")
            return None

    def websocket_single_request(
        self, ws_url, duration, round_num, client_num, request_num
    ):
        """单次WebSocket连接请求"""
        device_mac = self.device_mac_entry.get().strip()
        ws = None

        try:
            self.log(
                f"[轮次{round_num}][客户端{client_num}][请求{request_num}] 开始连接WebSocket",
                "INFO",
            )

            # 创建WebSocket连接
            ws = websocket.WebSocket()
            ws.connect(ws_url, timeout=10)

            self.log(
                f"[轮次{round_num}][客户端{client_num}][请求{request_num}] 连接成功",
                "SUCCESS",
            )

            # 发送hello消息
            hello_msg = {
                "type": "hello",
                "device_id": device_mac,
                "device_name": "Web测试设备",
                "device_mac": device_mac,
                "token": "your-token1",
                "features": {"mcp": True},
            }
            ws.send(json.dumps(hello_msg))
            self.log(
                f"[轮次{round_num}][客户端{client_num}][请求{request_num}] 已发送hello消息",
                "INFO",
            )

            # 等待服务器响应
            ws.settimeout(5)
            response = ws.recv()
            response_data = json.loads(response)

            if response_data.get("type") == "hello":
                self.log(
                    f"[轮次{round_num}][客户端{client_num}][请求{request_num}] 收到服务器hello响应",
                    "SUCCESS",
                )

                # 发送listen消息
                listen_msg = {
                    "type": "listen",
                    "mode": "manual",
                    "state": "detect",
                    "text": "你好",
                }
                ws.send(json.dumps(listen_msg))
                self.log(
                    f"[轮次{round_num}][客户端{client_num}][请求{request_num}] 已发送listen消息",
                    "INFO",
                )

                # 持续接收消息直到超时
                ws.settimeout(1)
                start_time = time.time()
                message_count = 0

                while time.time() - start_time < duration and self.is_testing:
                    try:
                        msg = ws.recv()
                        message_count += 1
                        if message_count % 10 == 0:
                            self.log(
                                f"[轮次{round_num}][客户端{client_num}][请求{request_num}] 已接收{message_count}条消息",
                                "INFO",
                            )
                    except websocket.WebSocketTimeoutException:
                        continue
                    except Exception as e:
                        self.log(
                            f"[轮次{round_num}][客户端{client_num}][请求{request_num}] 接收消息异常: {str(e)}",
                            "WARNING",
                        )
                        break

                self.log(
                    f"[轮次{round_num}][客户端{client_num}][请求{request_num}] 完成，共接收{message_count}条消息",
                    "SUCCESS",
                )
            else:
                self.log(
                    f"[轮次{round_num}][客户端{client_num}][请求{request_num}] 服务器响应类型不正确",
                    "ERROR",
                )

        except Exception as e:
            self.log(
                f"[轮次{round_num}][客户端{client_num}][请求{request_num}] 失败: {str(e)}",
                "ERROR",
            )
        finally:
            if ws:
                try:
                    ws.close()
                    self.log(
                        f"[轮次{round_num}][客户端{client_num}][请求{request_num}] 连接已关闭",
                        "INFO",
                    )
                except:
                    pass

    def websocket_client_worker(
        self, ws_url, duration, requests_per_round, round_num, client_num
    ):
        """单个客户端的测试工作线程，负责循环发起多次WebSocket连接"""
        for request_num in range(1, requests_per_round + 1):
            if not self.is_testing:
                break

            self.websocket_single_request(
                ws_url, duration, round_num, client_num, request_num
            )

            # 短暂延迟，避免请求过快
            time.sleep(0.5)

    def run_test_rounds(self):
        """执行多轮测试，持续循环直到用户停止"""
        try:
            # 获取测试参数
            client_count = int(self.client_count_entry.get())
            duration = int(self.duration_entry.get())
            requests_per_round = int(self.requests_per_round_entry.get())
            rest_time = int(self.rest_time_entry.get())

            # 获取WebSocket URL
            ws_url = self.get_websocket_url()
            if not ws_url:
                self.log("无法获取WebSocket地址，测试终止", "ERROR")
                self.stop_test()
                return

            self.log(
                f"测试配置 - 客户端数: {client_count}, 每轮次数: {requests_per_round}, 持续时间: {duration}秒, 休息时间: {rest_time}秒",
                "INFO",
            )

            # 持续执行测试，直到用户停止
            round_num = 1
            while self.is_testing:
                self.log(
                    f"========== 开始第 {round_num} 轮测试 ==========",
                    "INFO",
                )

                # 创建客户端线程
                threads = []
                for client_num in range(1, client_count + 1):
                    if not self.is_testing:
                        break

                    thread = threading.Thread(
                        target=self.websocket_client_worker,
                        args=(
                            ws_url,
                            duration,
                            requests_per_round,
                            round_num,
                            client_num,
                        ),
                    )
                    thread.daemon = True
                    thread.start()
                    threads.append(thread)
                    time.sleep(0.1)  # 避免同时发起太多连接

                # 等待所有线程完成
                for thread in threads:
                    thread.join()

                if not self.is_testing:
                    break

                self.log(
                    f"========== 第 {round_num} 轮测试完成 ==========",
                    "SUCCESS",
                )

                # 休息一段时间后开始下一轮
                if self.is_testing:
                    self.log(f"休息 {rest_time} 秒后开始下一轮...", "INFO")
                    for i in range(rest_time):
                        if not self.is_testing:
                            break
                        time.sleep(1)

                round_num += 1

            self.log("测试已停止", "WARNING")
            self.stop_test()

        except Exception as e:
            self.log(f"测试执行异常: {str(e)}", "ERROR")
            self.stop_test()

    def start_test(self):
        """开始测试"""
        if self.is_testing:
            return

        self.is_testing = True
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)

        self.log("========== 测试开始 ==========", "INFO")

        # 启动测试线程
        test_thread = threading.Thread(target=self.run_test_rounds)
        test_thread.daemon = True
        test_thread.start()

    def stop_test(self):
        """停止测试"""
        if not self.is_testing:
            return

        self.is_testing = False
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)

        self.log("========== 测试已停止 ==========", "WARNING")

    def get_process_stats_by_port(self, port=8000):
        """获取监听指定端口的进程内存和CPU使用情况"""
        try:
            for proc in psutil.process_iter(["pid", "name", "username"]):
                try:
                    # 获取进程打开的所有连接
                    connections = proc.net_connections(kind="inet")
                    for conn in connections:
                        # 检查端口是否匹配
                        if conn.laddr.port == port:
                            # 获取物理内存使用量（以MB为单位）
                            memory_info = proc.memory_info()
                            memory_mb = memory_info.rss / (1024 * 1024)
                            # 获取CPU使用率（百分比）
                            cpu_percent = proc.cpu_percent(interval=0.1)
                            return memory_mb, cpu_percent
                except (
                    psutil.NoSuchProcess,
                    psutil.AccessDenied,
                    psutil.ZombieProcess,
                ):
                    pass
            return 0, 0
        except Exception:
            return 0, 0

    def start_memory_monitor(self):
        """启动内存和CPU监控"""

        def monitor():
            first_check = True
            while True:
                memory_mb, cpu_percent = self.get_process_stats_by_port(8000)
                self.memory_data.append(memory_mb)
                self.cpu_data.append(cpu_percent)

                # 第一次检查时记录日志
                if first_check:
                    if memory_mb > 0:
                        self.log(
                            f"检测到8000端口进程，当前内存: {memory_mb:.2f} MB, CPU: {cpu_percent:.1f}%",
                            "SUCCESS",
                        )
                    else:
                        self.log(
                            "未检测到8000端口的进程，监控将持续尝试...", "WARNING"
                        )
                    first_check = False

                # 只保留最近100个数据点
                if len(self.memory_data) > 100:
                    self.memory_data.pop(0)
                if len(self.cpu_data) > 100:
                    self.cpu_data.pop(0)

                # 更新显示
                self.root.after(0, self.update_memory_display)

                time.sleep(2)  # 每2秒更新一次

        monitor_thread = threading.Thread(target=monitor)
        monitor_thread.daemon = True
        monitor_thread.start()

    def draw_memory_chart(self, canvas, memory_data, cpu_data, padding_left=50, padding_right=50):
        """在指定Canvas上绘制内存和CPU双曲线图表"""
        canvas.delete("all")

        width = canvas.winfo_width()
        height = canvas.winfo_height()

        if width <= 1 or height <= 1 or not memory_data:
            return

        # 过滤有效数据
        valid_memory = [m for m in memory_data if m > 0]
        valid_cpu = [c for c in cpu_data if c > 0]

        if not valid_memory and not valid_cpu:
            canvas.create_text(
                width / 2, height / 2, text="无数据", font=("Arial", 10), fill="gray"
            )
            return

        # 计算内存Y轴范围（左侧）
        if valid_memory:
            max_memory = max(valid_memory)
            min_memory = min(valid_memory)
            mem_range = max_memory - min_memory
            if mem_range < 10:
                mem_range = 10
            mem_y_min = max(0, min_memory - mem_range * 0.1)
            mem_y_max = max_memory + mem_range * 0.1
        else:
            mem_y_min, mem_y_max = 0, 100

        # 计算CPU Y轴范围（右侧，动态范围支持多核CPU超过100%）
        if valid_cpu:
            max_cpu = max(valid_cpu)
            min_cpu = min(valid_cpu)
            cpu_range = max_cpu - min_cpu
            if cpu_range < 10:
                cpu_range = 10
            cpu_y_min = max(0, min_cpu - cpu_range * 0.1)
            cpu_y_max = max(100, max_cpu + cpu_range * 0.1)  # 至少显示到100%
        else:
            cpu_y_min, cpu_y_max = 0, 100

        draw_width = width - padding_left - padding_right

        # 绘制网格线和左侧Y轴标签（内存）
        for i in range(5):
            y = height * i / 4
            canvas.create_line(padding_left, y, width - padding_right, y, fill="#e0e0e0", dash=(2, 2))

            # 左侧Y轴标签（内存，蓝色）
            mem_value = mem_y_max - (mem_y_max - mem_y_min) * i / 4
            canvas.create_text(
                padding_left - 5,
                y,
                text=f"{mem_value:.1f}",
                font=("Arial", 8),
                fill="#4169E1",
                anchor="e",
            )

            # 右侧Y轴标签（CPU，橙色）
            cpu_value = cpu_y_max - (cpu_y_max - cpu_y_min) * i / 4
            canvas.create_text(
                width - padding_right + 5,
                y,
                text=f"{cpu_value:.0f}%",
                font=("Arial", 8),
                fill="#FF8C00",
                anchor="w",
            )

        # 添加图例
        canvas.create_line(padding_left + 10, 10, padding_left + 40, 10, fill="#4169E1", width=2)
        canvas.create_text(padding_left + 45, 10, text="内存(MB)", font=("Arial", 8), fill="#4169E1", anchor="w")

        canvas.create_line(padding_left + 120, 10, padding_left + 150, 10, fill="#FF8C00", width=2)
        canvas.create_text(padding_left + 155, 10, text="CPU(%)", font=("Arial", 8), fill="#FF8C00", anchor="w")

        # 绘制内存曲线（蓝色）
        if len(memory_data) > 1 and valid_memory:
            points = []
            for i, memory in enumerate(memory_data):
                x = padding_left + draw_width * i / max(len(memory_data) - 1, 1)
                if memory > 0:
                    y = height - (height * (memory - mem_y_min) / (mem_y_max - mem_y_min))
                else:
                    y = height
                points.append((x, y, memory))

            # 绘制折线
            for i in range(len(points) - 1):
                if points[i][2] > 0 and points[i + 1][2] > 0:
                    canvas.create_line(
                        points[i][0],
                        points[i][1],
                        points[i + 1][0],
                        points[i + 1][1],
                        fill="#4169E1",
                        width=2,
                    )

            # 绘制数据点
            valid_points = [(x, y, m) for x, y, m in points if m > 0]
            for x, y, _ in valid_points:
                canvas.create_oval(
                    x - 3, y - 3, x + 3, y + 3, fill="#4169E1", outline="#4169E1"
                )

            # 标注最后一个值
            if valid_points:
                last_x, last_y, last_mem = valid_points[-1]
                canvas.create_text(
                    last_x,
                    last_y - 15,
                    text=f"{last_mem:.1f}",
                    font=("Arial", 9, "bold"),
                    fill="#4169E1",
                )

        # 绘制CPU曲线（橙色）
        if len(cpu_data) > 1 and valid_cpu:
            points = []
            for i, cpu in enumerate(cpu_data):
                x = padding_left + draw_width * i / max(len(cpu_data) - 1, 1)
                if cpu > 0:
                    y = height - (height * (cpu - cpu_y_min) / (cpu_y_max - cpu_y_min))
                else:
                    y = height
                points.append((x, y, cpu))

            # 绘制折线
            for i in range(len(points) - 1):
                if points[i][2] > 0 and points[i + 1][2] > 0:
                    canvas.create_line(
                        points[i][0],
                        points[i][1],
                        points[i + 1][0],
                        points[i + 1][1],
                        fill="#FF8C00",
                        width=2,
                    )

            # 绘制数据点
            valid_points = [(x, y, c) for x, y, c in points if c > 0]
            for x, y, _ in valid_points:
                canvas.create_oval(
                    x - 2, y - 2, x + 2, y + 2, fill="#FF8C00", outline="#FF8C00"
                )

            # 标注最后一个值
            if valid_points:
                last_x, last_y, last_cpu = valid_points[-1]
                canvas.create_text(
                    last_x,
                    last_y + 15,
                    text=f"{last_cpu:.1f}%",
                    font=("Arial", 9, "bold"),
                    fill="#FF8C00",
                )

    def update_memory_display(self):
        """更新内存和CPU监控显示"""
        if not self.memory_data or not self.cpu_data:
            self.memory_label.config(text="未检测到8000端口的进程")
            return

        # 过滤有效数据
        valid_memory = [m for m in self.memory_data if m > 0]
        valid_cpu = [c for c in self.cpu_data if c > 0]

        if not valid_memory and not valid_cpu:
            self.memory_label.config(text="未检测到8000端口的进程")
            return

        current_memory = self.memory_data[-1]
        current_cpu = self.cpu_data[-1]

        # 更新标签
        if current_memory == 0:
            max_memory = max(valid_memory) if valid_memory else 0
            max_cpu = max(valid_cpu) if valid_cpu else 0
            self.memory_label.config(
                text=f"进程已停止 | 历史峰值: 内存 {max_memory:.2f} MB | CPU {max_cpu:.1f}%"
            )
        else:
            max_memory = max(valid_memory) if valid_memory else 0
            min_memory = min(valid_memory) if valid_memory else 0
            max_cpu = max(valid_cpu) if valid_cpu else 0
            self.memory_label.config(
                text=f"当前: 内存 {current_memory:.2f} MB | CPU {current_cpu:.1f}% | 峰值: 内存 {max_memory:.2f} MB | CPU {max_cpu:.1f}%"
            )

        # 绘制完整趋势图（所有数据）
        self.draw_memory_chart(
            self.memory_canvas_full,
            list(self.memory_data),
            list(self.cpu_data),
            padding_left=50,
            padding_right=50
        )

        # 绘制最近10个数据点的放大视图
        recent_memory = (
            list(self.memory_data)[-10:]
            if len(self.memory_data) >= 10
            else list(self.memory_data)
        )
        recent_cpu = (
            list(self.cpu_data)[-10:]
            if len(self.cpu_data) >= 10
            else list(self.cpu_data)
        )
        self.draw_memory_chart(
            self.memory_canvas_recent,
            recent_memory,
            recent_cpu,
            padding_left=50,
            padding_right=50
        )


def main():
    root = tk.Tk()
    app = WebSocketTestTool(root)
    root.mainloop()


if __name__ == "__main__":
    main()

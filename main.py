import os
import zipfile
from astrbot.api.message_components import *
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
import jmcomic
import asyncio
import shutil

@register("JMdownloader", "FateTrial", "下载JM本子并加密压缩为ZIP", "1.0.1")
class JMPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.downloading = set()
        self.zip_password = "noworld"  # 默认密码
        
        # 定义路径
        self.plugin_root = "./data/plugins/jinman"
        self.zip_dir = os.path.join(self.plugin_root, "zip")  # 压缩包存储路径
        self.temp_dir = os.path.join(self.plugin_root, "picture")  # 临时下载目录
        
        # 确保目录存在
        os.makedirs(self.zip_dir, exist_ok=True)
        os.makedirs(self.temp_dir, exist_ok=True)

    async def download_and_zip(self, album_id, password):
        """下载本子并压缩为加密ZIP"""
        try:
            # 1. 下载图片到临时目录
            album_temp_dir = os.path.join(self.temp_dir, album_id)
            option = jmcomic.create_option_by_file(os.path.join(os.path.dirname(__file__), "option.yml"))
            option.download_dir = album_temp_dir  # 强制指定下载路径
            
            await asyncio.to_thread(jmcomic.download_album, album_id, option)
            
            # 2. 压缩为加密ZIP
            zip_path = os.path.join(self.zip_dir, f"{album_id}.zip")
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, _, files in os.walk(album_temp_dir):
                    for file in files:
                        if file.lower().endswith(('.jpg', '.png', '.webp')):
                            file_path = os.path.join(root, file)
                            zipf.write(
                                file_path,
                                arcname=os.path.relpath(file_path, album_temp_dir),
                                pwd=password.encode('utf-8')  # 加密
                            )
            
            # 3. 清理临时文件
            shutil.rmtree(album_temp_dir)
            
            return True, zip_path
        except Exception as e:
            # 清理可能残留的临时文件
            if 'album_temp_dir' in locals() and os.path.exists(album_temp_dir):
                shutil.rmtree(album_temp_dir, ignore_errors=True)
            return False, str(e)

    @filter.command("jm下载")
    async def JMid(self, event: AstrMessageEvent):
        messages = event.get_messages()
        if not messages or len(messages[0].text.split()) < 2:
            yield event.plain_result("用法: /jm下载 本子ID [密码]")
            return

        parts = messages[0].text.split()
        jm_id = parts[1]
        password = parts[2] if len(parts) >= 3 else self.zip_password
        zip_path = os.path.join(self.zip_dir, f"{jm_id}.zip")

        if os.path.exists(zip_path):
            yield event.plain_result(f"本子 {jm_id} 已存在")
            yield event.chain_result([File(name=f"{jm_id}.zip", file=zip_path)])
            return

        yield event.plain_result(f"开始下载并压缩本子 {jm_id}...")
        success, result = await self.download_and_zip(jm_id, password)
        
        if success:
            yield event.plain_result("下载完成！")
            yield event.chain_result([File(name=f"{jm_id}.zip", file=result)])
        else:
            yield event.plain_result(f"失败: {result}")

    @filter.command("jm_help")
    async def show_help(self, event: AstrMessageEvent):
        help_text = """指令说明:
/jm下载 本子ID [密码] - 下载并加密压缩(默认密码:noworld)
/jm_help - 显示帮助"""
        yield event.plain_result(help_text)

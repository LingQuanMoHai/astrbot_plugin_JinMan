from astrbot.api.message_components import *
from astrbot.api.message_components import File
from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api.all import *

import httpx
import json
import asyncio
import os
import time
import zipfile
import shutil

import jmcomic

@register("JMdownloader", "LingQuanMoHai", "一个下载JM本子的插件,修复了不能下载仅登录查看的本子请自行配置cookies", "0.0.1")
class JMPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.downloading = set() # 存储正在下载的ID
        self.zip_password = "noworld"
        
        # 确保目录存在
        os.makedirs(f"{os.path.abspath(os.path.dirname(__file__))}/picture", exist_ok=True)
        os.makedirs(f"{os.path.abspath(os.path.dirname(__file__))}/zips", exist_ok=True)

    async def download_comic_async(self, album_id, option):
        if album_id in self.downloading:
            return False, "该本子正在下载中，请稍后再试"
            
        self.downloading.add(album_id)
        try:
            await asyncio.to_thread(jmcomic.download_album, album_id, option)
            return True, None
        except Exception as e:
            return False, f"下载出错: {str(e)}"
        finally:
            self.downloading.discard(album_id)

    async def create_zip(self, source_dir, output_path, password):
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(source_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, source_dir)
                    zipf.write(file_path, arcname, pwd=password.encode() if password else None)

    @filter.command("jm下载")
    async def JMid(self, event: AstrMessageEvent):
        path = os.path.abspath(os.path.dirname(__file__))
        messages = event.get_messages()

        if not messages:
            yield event.plain_result("请输入要下载的本子ID,如果有多页，请输入第一页的ID")
            return
            
        message_text = messages[0].text  
        parts = message_text.split()  
        if len(parts) < 2:  
            yield event.plain_result("请输入要下载的本子ID,如果有多页，请输入第一页的ID")
            return
         
        if len(parts) >= 3:
            jm_id = parts[1]
            password = parts[2]
        else:
            jm_id = parts[1]
            password = self.zip_password
            
        zip_path = f"{path}/zips/{jm_id}.zip"
        comic_dir = f"{path}/picture/{jm_id}"

        if os.path.exists(zip_path):
            yield event.plain_result(f"本子 {jm_id} 已存在，直接发送")
            yield event.chain_result([File(name=f"{jm_id}.zip", file=zip_path)])
            return
            
        yield event.plain_result(f"开始下载本子 {jm_id}，请稍候...")
        option = jmcomic.create_option_by_file(f"{path}/option.yml")
        
        success, error_msg = await self.download_comic_async(jm_id, option)
        
        if not success:
            yield event.plain_result(error_msg)
            return
            
        if os.path.exists(comic_dir):
            await self.create_zip(comic_dir, zip_path, password)
            shutil.rmtree(comic_dir)  # 删除原始文件
            
        if os.path.exists(zip_path):
            yield event.plain_result(f"本子 {jm_id} 下载完成")
            yield event.chain_result([File(name=f"{jm_id}.zip", file=zip_path)])
        else:
            yield event.plain_result(f"下载完成，但未找到生成的文件")

    @filter.command("jm_help")
    async def show_help(self, event: AstrMessageEvent):
        help_text = """JM下载插件指令说明：
        
/jm下载 本子ID - 下载JM漫画 如果有多页，请输入第一页的ID
/jm下载 本子ID 密码 - 使用自定义密码压缩
/jm_help - 显示本帮助信息
powerd by FateTrial
"""
        yield event.plain_result(help_text)

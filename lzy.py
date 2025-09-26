from curl_cffi import requests
import re
import sys
import os
import subprocess
from tkinter import messagebox
from urllib.parse import quote


def get_lanzou_download_link(folder_url, password, file_to_find):
    """
    This function is a Python translation of the logic in lzy.e.
    It gets a direct download link for a file in a Lanzou folder.
    """
    try:
        # Part 1: Get file list
        base_url_match = re.search(r"https://([^/]+)", folder_url)
        if not base_url_match:
            raise ValueError(f"无法从 '{folder_url}' 中提取基础 URL")
        base_url = base_url_match.group(1)

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 Edg/132.0.0.0",
            "Referer": f"https://{base_url}/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
        }

        r = requests.get(
            folder_url, headers=headers, impersonate="chrome", allow_redirects=True
        )
        r.raise_for_status()
        page_text = r.text

        t_var = re.search(r"'t':\s*(\w+)", page_text).group(1)
        t_val = re.search(rf"var {t_var}\s*=\s*'(\d+)'", page_text).group(1)
        k_var = re.search(r"'k':\s*(\w+)", page_text).group(1)
        k_val = re.search(rf"var {k_var}\s*=\s*'([a-f0-9]+)'", page_text).group(1)
        fid = re.search(r"'fid':\s*(\d+)", page_text).group(1)
        uid = re.search(r"'uid':\s*'(\d+)'", page_text).group(1)
        lx = re.search(r"'lx':\s*(\d+)", page_text).group(1)
        up = re.search(r"'up':\s*(\d+)", page_text).group(1)
        rep = re.search(r"'rep':\s*'(\d+)'", page_text).group(1)
        pg = re.search(r"pgs\s*=\s*(\d+);", page_text).group(1)
        ls = re.search(r"'ls':\s*(\d+)", page_text).group(1)

        post_data = f"lx={lx}&fid={fid}&uid={uid}&pg={pg}&rep={rep}&t={t_val}&k={k_val}&up={up}&ls={ls}&pwd={password}"

        ajax_url = f"https://{base_url}/filemoreajax.php?file={fid}"
        headers["Content-Type"] = "application/x-www-form-urlencoded"

        r = requests.post(
            ajax_url, data=post_data, headers=headers, impersonate="chrome"
        )
        r.raise_for_status()
        file_list = r.json()

        # Part 2: Find file and get its page
        file_id = None
        for file_info in file_list.get("text", []):
            print(file_info.get("name_all"))
            if file_info.get("name_all") == file_to_find:
                file_id = file_info.get("id")
                break

        if not file_id:
            raise ValueError(f"文件 '{file_to_find}' 在文件夹中未找到。")

        # Part 3: Get download link
        file_page_url = f"https://{base_url}/{file_id}"
        r = requests.get(
            file_page_url, headers=headers, impersonate="chrome", allow_redirects=True
        )
        r.raise_for_status()
        page_text = r.text

        fn_path = re.search(r'src="/(fn\?[^"]+)"', page_text).group(1)

        fn_url = f"https://{base_url}/{fn_path}"
        r = requests.get(
            fn_url, headers=headers, impersonate="chrome", allow_redirects=True
        )
        r.raise_for_status()
        page_text = r.text

        file_id_final = re.search(r"file='(\d+)'", page_text).group(1)
        action_val = re.search(r"'action':'([^']+)'", page_text).group(1)

        signs_var = re.search(r"'signs':\s*(\w+)", page_text).group(1)
        signs_val = re.search(rf"var {signs_var}\s*=\s*'([\w\d]+)'", page_text).group(1)

        sign_var = re.search(r"'sign':\s*(\w+)", page_text).group(1)
        sign_val = re.search(rf"var {sign_var}\s*=\s*'([\w\d\.]*)'", page_text).group(1)

        websign_val = re.search(r"'websign':'([^']+)'", page_text).group(1)
        websignkey_var = re.search(r"'websignkey':\s*(\w+)", page_text).group(1)
        websignkey_val = re.search(
            rf"var {websignkey_var}\s*=\s*'([\w\d]+)'", page_text
        ).group(1)

        final_post_data = f"action={action_val}&signs={quote(signs_val)}&sign={sign_val}&websign={websign_val}&websignkey={websignkey_val}&ves=1&kd=1"

        ajaxm_url = f"https://{base_url}/ajaxm.php?file={file_id_final}"

        r = requests.post(
            ajaxm_url, data=final_post_data, headers=headers, impersonate="chrome"
        )
        r.raise_for_status()

        download_info = r.json()

        if download_info.get("url"):
            return f"{download_info['dom']}/file/{download_info['url']}"
        else:
            raise ValueError(f"获取下载链接失败: {download_info.get('info')}")

    except Exception as e:
        messagebox.showerror("错误", f"处理失败: {e}")
        return None


def create_bat_file(title):
    # 生成临时 bat 文件的完整路径
    bat_file_path = os.path.join(os.getcwd(), "up.bat")

    # 获取当前运行 exe 文件的完整路径
    exe_file_path = os.path.abspath(sys.argv[0])

    # 创建批处理文件用于删除当前运行的 exe 文件
    bat_content = f"""
@echo off
start "" "{os.path.join(os.getcwd(), title)}"
:loop
ping 127.0.0.1 -n 3 >nul
del "{exe_file_path}"
if exist "{exe_file_path}" (
    goto loop
) else (
    del %0
)
"""

    # 写入 bat 文件
    with open(bat_file_path, "w", encoding="utf-8") as f:
        f.write(bat_content.strip())

    # 使用 subprocess 启动批处理文件
    subprocess.Popen(bat_file_path, creationflags=subprocess.CREATE_NEW_CONSOLE)

    # 确保当前程序退出
    sys.exit()


if __name__ == "__main__":
    # 这是一个示例用法，请根据您的需求修改
    FOLDER_URL = "https://kedaya798.lanzouu.com/b0w8fxfwb"
    PASSWORD = "kedaya"
    FILE_TO_FIND = "lzy.dll"  # 您要查找的文件名

    print(f"正在从文件夹 '{FOLDER_URL}' 中查找文件 '{FILE_TO_FIND}'...")
    download_link = get_lanzou_download_link(FOLDER_URL, PASSWORD, FILE_TO_FIND)

    if download_link:
        print(f"成功获取下载链接: {download_link}")

        # 如果需要，可以在此处添加下载文件的逻辑
        # print("正在下载文件...")
        # file_content = requests.get(download_link).content
        # with open(FILE_TO_FIND, "wb") as f:
        #     f.write(file_content)
        # print("下载完成！")

    else:
        print("获取下载链接失败。")

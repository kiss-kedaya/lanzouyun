from curl_cffi import requests
import re
import sys
import os
import subprocess
from tkinter import messagebox
from urllib.parse import quote


def get_lanzou_download_link(folder_url, password, mode="latest", selector=None):
    """
    This function is a Python translation of the logic in lzy.e, with added features.
    It gets a direct download link for a file in a Lanzou folder.

    :param folder_url: The URL of the Lanzou folder.
    :param password: The password for the folder.
    :param mode: 'latest', 'filename', or 'description'.
    :param selector: The filename or description to search for, depending on the mode.
    :return: A tuple (download_link, folder_description, file_description) or (None, None, None).
    """
    try:
        folder_desc = ""
        file_desc = ""

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

        description_match = re.search(r'<span id="filename">([^<]+)</span>', page_text)
        if description_match:
            folder_desc = description_match.group(1)
            print(f"文件夹说明: {folder_desc}")

        try:
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
        except AttributeError:
            raise ValueError("无法从文件夹页面提取所有必需的参数。页面结构可能已更改。")

        post_data = f"lx={lx}&fid={fid}&uid={uid}&pg={pg}&rep={rep}&t={t_val}&k={k_val}&up={up}&ls={ls}&pwd={password}"

        ajax_url = f"https://{base_url}/filemoreajax.php?file={fid}"
        headers["Content-Type"] = "application/x-www-form-urlencoded"

        r = requests.post(
            ajax_url, data=post_data, headers=headers, impersonate="chrome"
        )
        r.raise_for_status()
        file_list = r.json()

        # Part 2: Find file based on mode
        target_file_info = None
        file_page_text_for_part3 = None  # Optimization for description mode

        if mode == "latest":
            if file_list.get("text"):
                target_file_info = file_list["text"][0]
        elif mode == "filename":
            if not selector:
                raise ValueError("文件名模式需要提供 selector (文件名)。")
            for file_info in file_list.get("text", []):
                if file_info.get("name_all") == selector:
                    target_file_info = file_info
                    break
        elif mode == "description":
            if not selector:
                raise ValueError("文件描述模式需要提供 selector (描述内容)。")
            print(
                "警告: 'description' 模式需要检查文件夹中的每个文件页面，可能会很慢。"
            )
            for file_info in file_list.get("text", []):
                temp_file_id = file_info.get("id")
                temp_file_page_url = f"https://{base_url}/{temp_file_id}"
                r_file = requests.get(
                    temp_file_page_url,
                    headers=headers,
                    impersonate="chrome",
                    allow_redirects=True,
                )
                r_file.raise_for_status()
                page_text = r_file.text
                desc_match = re.search(
                    r'<span class="p7">文件描述：</span><br>([^<]+)', page_text
                )
                if desc_match:
                    description = desc_match.group(1).strip()
                    if selector in description:
                        target_file_info = file_info
                        file_page_text_for_part3 = page_text
                        file_desc = description
                        break
        else:
            raise ValueError(f"不支持的模式: {mode}")

        if not target_file_info:
            raise ValueError(f"在模式 '{mode}' 和选择器 '{selector}' 下未找到文件。")

        file_id = target_file_info.get("id")
        print(f"已选择文件: {target_file_info.get('name_all')}")

        # Part 3: Get download link
        if file_page_text_for_part3:
            page_text = file_page_text_for_part3
        else:
            file_page_url = f"https://{base_url}/{file_id}"
            r = requests.get(
                file_page_url,
                headers=headers,
                impersonate="chrome",
                allow_redirects=True,
            )
            r.raise_for_status()
            page_text = r.text

        if not file_desc:
            description_match = re.search(
                r'<span class="p7">文件描述：</span><br>([^<]+)', page_text
            )
            if description_match:
                file_desc = description_match.group(1).strip()
                if file_desc:
                    print(f"文件详细描述: {file_desc}")

        # --- Detailed extraction with specific error handling ---
        fn_path_match = re.search(r'src="/(fn[^"]+)"', page_text)
        if not fn_path_match:
            raise ValueError("提取失败: fn_path")
        fn_path = fn_path_match.group(1)

        fn_url = f"https://{base_url}/{fn_path}"
        r = requests.get(
            fn_url, headers=headers, impersonate="chrome", allow_redirects=True
        )
        r.raise_for_status()
        page_text = r.text

        file_id_final_match = re.search(r"file=([^']*)',//data", page_text)
        if not file_id_final_match:
            raise ValueError("提取失败: file_id_final")
        file_id_final = file_id_final_match.group(1)

        action_val_match = re.search(r"'action':'([^']+)'", page_text)
        if not action_val_match:
            raise ValueError("提取失败: action_val")
        action_val = action_val_match.group(1)

        signs_var_match = re.search(r"'signs':\s*(\w+)", page_text)
        if not signs_var_match:
            raise ValueError("提取失败: signs_var")
        signs_var = signs_var_match.group(1)

        signs_val_match = re.search(rf"var {signs_var}\s*=\s*'([^']+)'", page_text)
        if not signs_val_match:
            raise ValueError("提取失败: signs_val")
        signs_val = signs_val_match.group(1)

        sign_var_match = re.search(r"'sign':\s*(\w+)", page_text)
        if not sign_var_match:
            raise ValueError("提取失败: sign_var")
        sign_var = sign_var_match.group(1)

        sign_val_match = re.search(rf"var {sign_var}\s*=\s*'([^']+)'", page_text)
        if not sign_val_match:
            raise ValueError("提取失败: sign_val")
        sign_val = sign_val_match.group(1)

        websign_val_match = re.search(r"'websign':'([^']+)'", page_text)
        if not websign_val_match:
            raise ValueError("提取失败: websign_val")
        websign_val = websign_val_match.group(1)

        websignkey_var_match = re.search(r"'websignkey':\s*(\w+)", page_text)
        if not websignkey_var_match:
            raise ValueError("提取失败: websignkey_var")
        websignkey_var = websignkey_var_match.group(1)

        websignkey_val_match = re.search(
            rf"var {websignkey_var}\s*=\s*'([^']+)'", page_text
        )
        if not websignkey_val_match:
            raise ValueError("提取失败: websignkey_val")
        websignkey_val = websignkey_val_match.group(1)

        final_post_data = f"action={action_val}&signs={quote(signs_val)}&sign={sign_val}&websign={websign_val}&websignkey={websignkey_val}&ves=1&kd=1"
        ajaxm_url = f"https://{base_url}/ajaxm.php?file={file_id_final}"

        r = requests.post(
            ajaxm_url, data=final_post_data, headers=headers, impersonate="chrome"
        )
        r.raise_for_status()
        download_info = r.json()

        if download_info.get("url"):
            download_link = f"{download_info['dom']}/file/{download_info['url']}"
            return download_link, folder_desc, file_desc
        else:
            raise ValueError(f"获取下载链接失败: {download_info.get('info')}")

    except Exception as e:
        messagebox.showerror("错误", f"处理失败: {e}")
        return None, None, None


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
    FOLDER_URL = "https://kedaya798.lanzouu.com/b0w8fxfwb"
    PASSWORD = "kedaya"

    # --- 示例 1: 获取最新文件 ---
    print("--- 模式: 获取最新文件 ---")
    link, folder_desc, file_desc = get_lanzou_download_link(
        FOLDER_URL, PASSWORD, mode="latest"
    )
    if link:
        print(f"成功获取下载链接: {link}")
        print(f"文件夹描述: {folder_desc}")
        print(f"文件描述: {file_desc}")
    print("\n" + "-" * 20 + "\n")

    # --- 示例 2: 按文件名查找 ---
    print("--- 模式: 按文件名查找 ---")
    FILE_TO_FIND = "lzy.dll"  # 您要查找的文件名
    link, folder_desc, file_desc = get_lanzou_download_link(
        FOLDER_URL, PASSWORD, mode="filename", selector=FILE_TO_FIND
    )
    if link:
        print(f"成功获取下载链接: {link}")
    print("\n" + "-" * 20 + "\n")

    # --- 示例 3: 按描述查找 (注意: 此模式可能很慢) ---
    print("--- 模式: 按描述查找 ---")
    DESC_TO_FIND = "我是描述"  # 您要查找的描述中的关键字
    link, folder_desc, file_desc = get_lanzou_download_link(
        FOLDER_URL, PASSWORD, mode="description", selector=DESC_TO_FIND
    )
    if link:
        print(f"成功获取下载链接: {link}")

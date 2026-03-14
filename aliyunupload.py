import oss2
import os

# --- 1. 配置区域 (请填入你的信息) ---
ACCESS_KEY_ID = os.getenv('OSS_ACCESS_KEY_ID', '')  # 你的 AccessKey ID
ACCESS_KEY_SECRET = os.getenv('OSS_ACCESS_KEY_SECRET', '')  # 你的 AccessKey Secret
BUCKET_NAME = os.getenv('OSS_BUCKET_NAME', '')  # 你的 Bucket 名称
ENDPOINT = os.getenv('OSS_ENDPOINT', 'oss-cn-beijing.aliyuncs.com')  # 你的 Endpoint (地域节点)

# 本地要上传的文件路径
LOCAL_FILE_PATH = './test.jpg'
# 上传到 OSS 后的路径 (相当于在网盘里的文件名，支持用 "/" 创建文件夹)
# 例如: 'images/2025/test.jpg'
OBJECT_NAME = 'uploads/test.jpg'


def upload_image():
    print(f"🔄 正在连接 OSS...")

    # --- 2. 身份验证 ---
    auth = oss2.Auth(ACCESS_KEY_ID, ACCESS_KEY_SECRET)

    # --- 3. 初始化 Bucket 实例 ---
    # 注意：Endpoint 不带 bucket 名，也不带 http:// (SDK会自动处理，或者你写 http:// 也可以)
    bucket = oss2.Bucket(auth, ENDPOINT, BUCKET_NAME)

    try:
        # --- 4. 上传文件 ---
        # put_object_from_file(OSS上的文件名, 本地文件名)
        result = bucket.put_object_from_file(OBJECT_NAME, LOCAL_FILE_PATH)

        if result.status == 200:
            print("✅ 上传成功！")

            # --- 5. 拼接公网 URL ---
            # 默认拼接逻辑： https://{bucket_name}.{endpoint}/{object_name}
            # 如果你的 Bucket 是“公共读”权限，这个链接可以直接访问
            file_url = f"https://{BUCKET_NAME}.{ENDPOINT}/{OBJECT_NAME}"

            print("🔗 图片直链:")
            print(file_url)
            return file_url
        else:
            print(f"❌ 上传失败，状态码: {result.status}")

    except oss2.exceptions.OssError as e:
        print(f"❌ 发生错误: {e}")


if __name__ == '__main__':
    if not ACCESS_KEY_ID or not ACCESS_KEY_SECRET or not BUCKET_NAME:
        print("错误: 请先配置环境变量 OSS_ACCESS_KEY_ID / OSS_ACCESS_KEY_SECRET / OSS_BUCKET_NAME")
        exit(1)

    # 确保本地有个测试文件，或者改一下 LOCAL_FILE_PATH
    if not os.path.exists(LOCAL_FILE_PATH):
        print(f"错误: 找不到本地文件 {LOCAL_FILE_PATH}，请先放一张图片在这里。")
    else:
        upload_image()

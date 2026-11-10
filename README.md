# Website Viettel Đồng Nai

## Chạy website và trang quản trị

Python 3.12 trở lên, không cần cài thư viện. Chạy tại thư mục kho mã:

```bash
read -rsp 'Mật khẩu quản trị (ít nhất 12 ký tự): ' ADMIN_PASSWORD
export ADMIN_PASSWORD
python3 server.py --bind 0.0.0.0 --port 8000
```

Trang bán hàng ở `/`, trang quản trị ở `/admin.html`. Đăng nhập bằng mật khẩu đã đặt trong `ADMIN_PASSWORD`. Không lưu mật khẩu trong Git. Mật khẩu dùng chung cho quản trị viên; phiên đăng nhập hết hạn sau 8 giờ và khi khởi động lại máy chủ.

Trang quản trị hỗ trợ tìm kiếm, lọc dịch vụ/trạng thái, thêm, sửa, ẩn và xóa gói. Tất cả nhóm dịch vụ và thiết bị Tendoo dùng chung danh mục. Mỗi lần mở bảng giá, website lấy dữ liệu mới từ máy chủ; form đăng ký sử dụng tên, giá và chi tiết của gói đã chọn. Thay đổi được lưu nguyên tử, có kiểm tra xung đột giữa các phiên quản trị.

SQLite lưu mặc định ở `../.web-ban-hang/catalog.sqlite3`, ngoài thư mục website. Có thể đặt `CATALOG_DB` thành đường dẫn trên ổ lưu trữ bền vững. Dữ liệu ban đầu lấy từ `data/plans.json` một lần khi tạo database. Sao lưu database để bảo toàn các thay đổi; không xóa database khi triển khai lại.

Để đưa lên Internet, triển khai tiến trình Python sau reverse proxy HTTPS, đặt `COOKIE_SECURE=1`, cung cấp `ADMIN_PASSWORD` qua cấu hình bảo mật và gắn ổ lưu trữ cho SQLite. Đây là ứng dụng máy chủ; GitHub Pages chỉ phục vụ giao diện tĩnh và **không hỗ trợ đăng nhập/lưu quản trị**. Khi chỉ phục vụ tĩnh, bảng giá dùng dữ liệu ban đầu từ JSON.

Không gửi form thật khi kiểm thử: FormSubmit gửi thông tin đến email tư vấn đã có trong website. Video và dịch vụ email phụ thuộc nhà cung cấp bên ngoài.

## Kiểm thử

```bash
python3 -m unittest discover -s tests -v
```

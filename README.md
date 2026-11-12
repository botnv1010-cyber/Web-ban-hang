# Website Viettel Đồng Nai

## Chạy website và trang quản trị

Python 3.12 trở lên, không cần cài thư viện. Chạy tại thư mục kho mã:

```bash
read -rsp 'Mật khẩu quản trị (ít nhất 12 ký tự): ' ADMIN_PASSWORD
export ADMIN_PASSWORD
python3 server.py --bind 0.0.0.0 --port 8000
```

Trang bán hàng ở `/`, trang quản trị ở `/admin.html`. Tên đăng nhập mặc định là `admin` (đổi qua `ADMIN_USERNAME`). Đăng nhập bằng mật khẩu đã đặt trong `ADMIN_PASSWORD`. Nếu không đặt biến mật khẩu, máy chủ đọc tài khoản từ tệp JSON riêng `../.web-ban-hang/admin.json` hoặc đường dẫn `ADMIN_CREDENTIAL_FILE`, gồm hai trường `username` và `password`. Giới hạn quyền tệp này về `600` và không đưa vào Git. Không lưu mật khẩu trong Git. Mật khẩu dùng chung cho quản trị viên; phiên đăng nhập hết hạn sau 8 giờ; đổi thông tin tài khoản sẽ vô hiệu hóa phiên cũ.

Trang quản trị hỗ trợ tìm kiếm, lọc dịch vụ/trạng thái, thêm, sửa, ẩn và xóa gói. Tất cả nhóm dịch vụ và thiết bị Tendoo dùng chung danh mục. Mỗi lần mở bảng giá, website lấy dữ liệu mới từ máy chủ; form đăng ký sử dụng tên, giá và chi tiết của gói đã chọn. Thay đổi được lưu nguyên tử, có kiểm tra xung đột giữa các phiên quản trị.

SQLite lưu mặc định ở `../.web-ban-hang/catalog.sqlite3`, ngoài thư mục website. Có thể đặt `CATALOG_DB` thành đường dẫn trên ổ lưu trữ bền vững. Dữ liệu ban đầu lấy từ `data/plans.json` một lần khi tạo database. Sao lưu database để bảo toàn các thay đổi; không xóa database khi triển khai lại.

Để đưa lên Internet, triển khai tiến trình Python sau reverse proxy HTTPS, đặt `COOKIE_SECURE=1`, cung cấp `ADMIN_PASSWORD` qua cấu hình bảo mật và gắn ổ lưu trữ cho SQLite. Đây là ứng dụng máy chủ; GitHub Pages chỉ phục vụ giao diện tĩnh và **không hỗ trợ đăng nhập/lưu quản trị**. Khi chỉ phục vụ tĩnh, bảng giá dùng dữ liệu ban đầu từ JSON.

Không gửi form thật khi kiểm thử: đăng ký sử dụng API email Resend ở phía máy chủ. Video và dịch vụ email phụ thuộc nhà cung cấp bên ngoài.

## Kiểm thử

```bash
python3 -m unittest discover -s tests -v
```

## Lỗi API không trả về JSON

Thông báo `Unexpected token 'T'` hoặc `Unexpected token '<'` thường xuất hiện khi máy chủ trả về trang lỗi/văn bản thay cho API JSON. Trang quản trị cần mở từ máy chủ chạy `server.py`, không phải `python3 -m http.server` hoặc GitHub Pages. Kiểm tra `/api/session`: máy chủ đúng trả HTTP 401 với JSON khi chưa đăng nhập. HTTP 404/405 hoặc HTML cho biết đường dẫn API không được phục vụ; HTTP 502/503 thường cần kiểm tra tiến trình Python và reverse proxy. Nếu website nằm dưới thư mục con, chuyển tiếp cả trang quản trị và đường dẫn `api/` cùng thư mục đến máy chủ Python.

## Triển khai trên Vercel

Kho mã có `vercel.json`, hàm Python `api/index.py` và bước build chỉ xuất các tệp giao diện vào `public/`. Các đường dẫn `/api/*` được chuyển đến hàm Python. Không sử dụng SQLite trên Vercel vì hệ thống tệp của Functions không phải nơi lưu dữ liệu bền vững.

1. Tạo PostgreSQL, ví dụ Neon qua Vercel Marketplace → Storage; kết nối vào project website.
2. Trong Vercel → Project → Settings → Environment Variables, đặt cho môi trường Production:
   - `DATABASE_URL`: chuỗi kết nối PostgreSQL do nhà cung cấp cấp, giữ cấu hình TLS của nhà cung cấp. `POSTGRES_URL` cũng được hỗ trợ nếu tích hợp đã cung cấp biến này.
   - `ADMIN_USERNAME`: `admin` hoặc tên bạn chọn.
   - `ADMIN_PASSWORD`: mật khẩu riêng ít nhất 12 ký tự, nhập qua giao diện bảo mật Vercel. Tệp tài khoản trong môi trường phát triển không được đưa lên Vercel/GitHub.
3. Framework Preset: Other. Dùng Build Command và Output Directory từ `vercel.json` (xóa các override cũ không phù hợp), rồi Redeploy.
4. Mở `/api/session`: nếu chưa đăng nhập, phản hồi đúng là HTTP 401 kèm JSON. Nếu nhận JSON 503, kiểm tra biến môi trường, kết nối cơ sở dữ liệu và Functions logs. Sau đó đăng nhập ở `/admin.html`, sửa thử một gói rồi xem lại bảng giá trên website.

Ứng dụng tự tạo các bảng cần thiết và nạp 111 gói ban đầu khi cơ sở dữ liệu còn trống. Catalog, phiên đăng nhập và bộ đếm giới hạn đăng nhập đều lưu trong PostgreSQL dùng chung giữa các Functions. Đổi mật khẩu/tên đăng nhập sẽ vô hiệu hóa các phiên cũ. Không dùng cùng cơ sở dữ liệu Production cho Preview nếu không muốn bản Preview thay đổi bảng giá thật.

## Yêu cầu tư vấn và email xác nhận

Form gửi đến `/api/registrations`, lưu yêu cầu vào database trước khi gửi email đến khách qua Resend. Số điện thoại tùy chọn; email và đồng ý liên hệ bắt buộc. Dùng `RESEND_API_KEY` và `RESEND_FROM_EMAIL` ở backend. Inbox quản trị hiển thị mã yêu cầu, trạng thái xử lý, trạng thái email và ID provider. Lỗi hoặc thiếu cấu hình email không làm mất yêu cầu đã lưu. Xem [hướng dẫn bàn giao](ADMIN-HANDOFF.md).

## Bộ nhớ đệm bảng giá

Website tải trước danh mục, dùng chung yêu cầu đang tải và lưu danh mục vào localStorage tối đa 24 giờ để mở “Xem chi tiết” ngay. Mỗi lần mở vẫn kiểm tra lại máy chủ ở nền bằng ETag; dữ liệu không đổi trả HTTP 304, không tải lại toàn bộ JSON. Cache không phải nguồn dữ liệu chính: đăng ký luôn xác nhận lại gói hiện hành và máy chủ vẫn kiểm tra giá từ database.

Sau khi admin lưu thành công, cache danh mục cùng trình duyệt được xóa và các tab website cùng origin nhận thông báo cập nhật. Trình duyệt/thiết bị khác kiểm tra khi mở bảng giá, quay lại trang hoặc mỗi 15 giây khi trang đang hiển thị. Đây là cập nhật định kỳ, không phải push tức thời giữa thiết bị. Khi mất mạng, bảng giá đã lưu có thể được hiển thị kèm thông báo; không tiếp tục chọn đăng ký nếu chưa xác nhận được dữ liệu mới. Trình duyệt chặn localStorage vẫn dùng được cache trong bộ nhớ của trang.

Máy chủ Python cho phép trình duyệt lưu tài nguyên tĩnh nhưng bắt buộc xác thực lại trước khi tái sử dụng. Các API tài khoản và phản hồi lưu dữ liệu vẫn dùng `no-store`. Luồng admin cần máy chủ Python hoặc Vercel có PostgreSQL; bản GitHub Pages tĩnh chỉ dùng danh mục JSON ban đầu.

## Quản trị nội dung và yêu cầu tư vấn

Xem [bảng phạm vi, cấu hình Neon/Blob/Resend, hướng dẫn Vercel Preview và kết quả kiểm tra](ADMIN-HANDOFF.md). Cấu hình email hiện hành dùng `RESEND_FROM_EMAIL` thay cho `MAIL_FROM`; email gửi đến khách. Yêu cầu được lưu cả khi gửi email lỗi.

# Phạm vi quản trị và bàn giao

Repository thực tế là website giải pháp số Viettel Đồng Nai, không phải một website chỉ bán gói di động. Có một trang khách `index.html`, các modal bảng giá/đăng ký và admin `admin.html`. Đã đọc các file HTML/CSS/JS, server Python, Vercel handler, dữ liệu 111 gói, scripts và tests. Không có trang tin tức, danh sách điểm giao dịch hay router/component framework riêng.

| Trang/phần hiện có | Nội dung/thao tác tĩnh | Admin đã nối | Cách đối chiếu |
|---|---|---|---|
| Header/menu | Nhãn và liên kết điều hướng | Nội dung website → HEADER | Sửa nhãn/link, tải lại, bấm menu |
| Banner đầu trang | 8 poster, link ảnh và thứ tự | Nội dung website → Banner; sửa ảnh/link, nhân bản, thứ tự, ẩn; tải ảnh tạo WebP 768/1920 | Tải ảnh, lưu; kiểm tra srcset và carousel trên điện thoại/máy tính |
| Địa chỉ chạy chữ | Địa chỉ viết cứng | Nội dung website → Địa chỉ | Sửa, tải lại, đối chiếu chữ chạy |
| Hero | Tiêu đề, thông điệp, ảnh và liên hệ | Nội dung website → tiêu đề giải pháp | Sửa từng trường, đối chiếu giao diện |
| Dải dịch vụ | Nội dung ticker | Nội dung website → Dải dịch vụ | Sửa và tải lại |
| Hệ sinh thái | Ảnh, mô tả, tên và liên kết 5 dịch vụ | Nội dung website → Hệ sinh thái | Sửa trường, tải lại và mở bảng giá |
| Bảng giá và thiết bị | 111 gói trong JSON và bản HTML cũ | Gói dịch vụ: thêm/sửa/xóa/ẩn, ↑ ↓ sắp xếp; mọi nút bảng giá dùng API chung | CRUD, kiểm tra giá/ẩn/thứ tự và chọn gói vào form |
| Khuyến mãi | Tiêu đề, poster, liên kết | Nội dung website → Khuyến mãi | Thay ảnh/link và tải lại |
| Video/tài nguyên | Tiêu đề, ảnh, URL video | Nội dung website → Video; URL YouTube embed | Đổi video, tải lại và phát |
| Tư vấn/liên hệ | Nội dung giới thiệu, ảnh, hotline | Nội dung website + Hotline toàn cục | Đổi hotline, tải lại, kiểm tra tel: |
| FAQ | Câu hỏi và textarea nháp chỉ lưu localStorage | Nội dung website → FAQ: câu hỏi/câu trả lời; bỏ bản nháp khách, chỉ đọc | Sửa câu trả lời, tải lại bằng trình duyệt khác |
| Footer | Một dòng viết cứng | Trường Footer riêng | Sửa, lưu, tải lại |
| Form tư vấn, form chọn gói | Chỉ gửi email tư vấn viên, mất yêu cầu nếu lỗi email | Lưu DB, trả mã, email khách, inbox và trạng thái | Đăng ký email hợp lệ, phone rỗng; xem inbox, đổi trạng thái |
| Admin | Có sẵn CRUD gói | Dùng lại CSS/form/table, thêm điều hướng nội dung và inbox | Kiểm tra đăng nhập, API 401, CSRF, đăng xuất |

Các trường nội dung dùng binding DOM theo thứ tự cố định của giao diện hiện có, không nhận HTML từ admin. Nhân bản tạo phần tử từ mẫu cùng loại; thứ tự áp dụng cho phần tử cùng cha. Khi thay cấu trúc HTML trong một nhiệm vụ lập trình sau này phải di trú binding trong `data/content.json`; không tự ghi đè nội dung đã được admin sửa. Với banner nên nhân bản trường ảnh; với FAQ nhân bản câu hỏi (kèm câu trả lời). Nhãn kỹ thuật như nút lưu, thông báo lỗi, label biểu mẫu vẫn thuộc mã giao diện, không phải nội dung marketing.

## Cấu hình Vercel và Neon

1. Tạo Neon project và branch riêng cho Preview, lấy connection string có `sslmode=require`. Không dùng branch Production cho Preview. Tạo Vercel Blob store và kết nối project; dùng public Blob store cho banner công khai.
2. Tại Vercel → Settings → Environment Variables, đặt các tên trong `.env.example` cho **Preview**: `DATABASE_URL`, `ADMIN_USERNAME`, `ADMIN_PASSWORD` (ít nhất 12 ký tự), `BLOB_READ_WRITE_TOKEN`, `RESEND_API_KEY`, `RESEND_FROM_EMAIL` (địa chỉ thuộc domain đã xác minh trong Resend). Không đưa giá trị vào Git, trình duyệt, NEXT_PUBLIC hay VITE variables. Vercel tự cấp Blob token khi liên kết store; dùng token của store Preview riêng.
3. Python 3.12+, cài `python3 -m pip install -r requirements.txt`. Khi DATABASE_URL đã được nạp an toàn vào process, chạy `python3 scripts/init_neon.py`. Lệnh tạo bảng và INSERT ON CONFLICT DO NOTHING, bảo toàn dữ liệu sửa. Handler cũng khởi tạo idempotent ở lần chạy đầu tiên.
4. Framework Other; build `python3 scripts/build_static.py`, output `public`; dùng `vercel.json`. Backend bundle gồm server/mailer/cms và data/*.json. Sau khi đổi biến môi trường phải redeploy.
5. Tạo nhánh Git riêng, import repository vào Vercel, deploy nhánh đó thành Preview. Vào **Deployment Protection**, bật Vercel Authentication cho Preview; nếu gói hỗ trợ có thể dùng Password Protection. Kiểm tra cửa sổ ẩn danh bị chặn trước khi chia sẻ URL Preview. Không đưa mật khẩu admin hay protection bypass token vào URL/changelog. Bảo vệ Preview là lớp riêng, không thay thế đăng nhập admin.
6. Mở `/admin` → đăng nhập. Sau khi lưu mỗi mục ở bảng trên, mở lại trang khách để so sánh. Chỉ publish production sau khi hoàn tất kiểm tra dịch vụ thật. `/admin.html` là shell đăng nhập công khai, dữ liệu inbox và mọi thao tác ghi được kiểm tra session/CSRF phía máy chủ; `/admin` chuyển người chưa đăng nhập về shell này.

## Email và dữ liệu khách hàng

Form giữ yêu cầu sau mọi kết quả gửi. `Chưa cấu hình email` khi thiếu khóa/địa chỉ gửi, `Gửi lỗi` khi timeout/provider từ chối, `Đã gửi` chỉ khi provider trả ID; ID lưu trong inbox. `Đã gửi` không đảm bảo thư đến inbox. Email gửi **đến khách**, chứa mã yêu cầu, thông tin gói lấy từ database và hotline hiện tại. Số điện thoại tùy chọn. Giới hạn 5 lần hợp lệ/IP/5 phút và idempotency theo requestId. Không tự động gửi lại email từ inbox; retry cùng mã không tạo yêu cầu/email trùng. Các yêu cầu trong admin giới hạn 500 mục mới nhất. Cần chính sách lưu giữ/xóa và sao lưu dữ liệu khách phù hợp khi vận hành.

## Kiểm chứng

- Bộ unittest: xác thực, CRUD/xung đột/cache gói; email với provider giả lập, kiểm tra email khách, lỗi vẫn lưu; thiếu cấu hình; phone tùy chọn; idempotency; seed chạy lại bảo toàn nội dung; tạo 2 ảnh WebP và upload giả lập.
- Chromium cục bộ: lưu và tải lại trường nội dung của cả 9 mục có nội dung chữ, kiểm tra binding ảnh responsive; đăng nhập qua `/admin`; sửa hotline/footer, tải lại khách thấy dữ liệu mới; API inbox chưa đăng nhập trả 401; gửi yêu cầu không có phone; xem inbox và đổi trạng thái.
- Kiểm tra cú pháp Python/JS và build tĩnh.
- **Chưa xác thực dịch vụ thật**: không có DATABASE_URL/Blob token/Resend key trong môi trường này. Chưa chạy migration trên Neon, upload Blob thật, nhận email thật hoặc dựng Vercel Preview có protection. Cần hoàn tất các bước cấu hình trên rồi kiểm tra lại toàn bộ bảng, đặc biệt carousel WebP và video trên thiết bị thật. Không khẳng định các mục chưa thử là đã đạt.

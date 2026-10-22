# ⚓️🛥️ BattleShip — Multiplayer (2-player) over TCP

## Tải Demo Chơi Thử

👉 **[Tải BattleShip-Client v1.0.0 (.ZIP)](https://github.com/<tên_tài_khoản_của_bạn>/battle-ship-game/releases/latest)**

> _Không cần cài đặt Python! Chỉ cần tải về, giải nén và chạy file `BattleShip-Client.exe`._

## Mô tả ngắn:

BattleShip là game chiến thuật 2 người chơi, mỗi phòng tối đa 2 người, chạy online qua TCP. Server quản lý nhiều phòng độc lập và lưu trạng thái bàn cùng lượt chơi. Dữ liệu trao đổi dùng JSON line (kết thúc \n) để dễ parse và mở rộng. Trò chơi gồm chế độ cổ điển (đặt tàu, bắn theo lượt, hit/miss/sunk, xử lý disconnect).

## Tính năng chính:

- Nhiều phòng (room), mỗi phòng tối đa 2 players.
- Đặt tàu, bắn theo lượt, thông báo hit / miss / sunk.
- Luật: bắn tiếp nếu trúng; hết tàu → thua.
- Xử lý rớt kết nối (thông báo đối phương thắng hoặc cho phép reconnect).

## Kiến trúc tổng quan:

- Server: TCP listener, map room_id -> GameRoom, mỗi client 1 thread, Lock khi chỉnh dữ liệu chung.
- Client: 2 luồng (recv + input), hiển thị 2 bảng (own/enemy).

## Trạng thái phòng (State):

- waiting — chưa đủ 2 người
- placing — cả 2 đang place ships
- playing — luân phiên bắn
- finished — game over, gửi winner

## Luồng chơi (flow):

1. Player A connect → join/create room.
2. Player B join same room → server gửi game_start + chỉ định lượt ngẫu nhiên.
3. Cả 2 gửi place_ships.
4. Khi cả 2 đã place → playing.
5. Player có lượt gửi shoot → server trả shot_result và broadcast.
6. Nếu tất cả tàu 1 bên chìm → finished.

## Cách chạy (Quick Start):

### 1. Yêu cầu môi trường (Prerequisites)

- **Python**: Khuyến nghị dùng Python **3.10 - 3.13**
- **Cài đặt thư viện**:

  ```sh
  pip install -r requirements.txt
  ```

  _(Tuỳ chọn) Nếu dùng môi trường ảo (venv):_

  ```sh
  # Tạo venv
  python -m venv venv

  # Kích hoạt venv (Windows)
  .\venv\Scripts\activate
  # Kích hoạt venv (Linux/macOS)
  # source venv/bin/activate

  # Cài đặt thư viện
  pip install -r requirements.txt
  ```

---

### 2. Khởi chạy trò chơi

**Bước 1: Khởi động Server** (mở terminal 1)

```sh
cd server/
python server.py
```

**Bước 2: Khởi động Người chơi 1 (Client-1)** (mở terminal 2)

```sh
cd client-ui/
python main.py
```

**Bước 3: Khởi động Người chơi 2 (Client-2)** (mở terminal 3)

```sh
cd client-ui/
python main.py
```

> **Lưu ý kết nối mạng:**
>
> - Mặc định client kết nối tới `127.0.0.1:8000`.
> - Nếu muốn đổi địa chỉ IP / Port server khác, bạn có thể thiết lập biến môi trường trước khi chạy client:
>   - Windows (PowerShell): `$env:BS_HOST="<IP_SERVER>"; $env:BS_PORT="8000"`
>   - Linux/macOS: `BS_HOST=<IP_SERVER> BS_PORT=8000 python main.py`

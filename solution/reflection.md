# Reflection (≤1 page)

Fill this in before you submit.

**Which fault types were hardest to catch, and why?**

Khó nhất là các lỗi lineage tinh vi và các lỗi AI-infra ở mức nhẹ. Những lỗi rõ như freshness, contract, hay drift lớn khá dễ bắt vì toolkit trả về các tín hiệu có thể đặt ngưỡng trực tiếp. Phần khó hơn là các trường hợp chỉ lộ ra qua tín hiệu tổng hợp: lineage phải suy luận từ `actual_upstream` và `actual_downstream_count`, còn feature skew nhẹ thì nằm rất sát baseline sạch, nên một ngưỡng tĩnh duy nhất không đủ tin cậy.

**What would you change about your cost/coverage tradeoff, if you had another pass?**

Nếu có thêm một lượt, tôi sẽ giữ đường mặc định thật rẻ và bảo thủ, rồi chỉ dùng kiểm tra bổ sung khi tín hiệu vòng đầu ở mức lưng chừng. Thực tế là một lần gọi tool cho đa số event, còn state hoặc slice sâu hơn chỉ dành cho lineage hay drift đáng ngờ. Tôi cũng sẽ tinh chỉnh ngưỡng theo từng pillar dựa trên hành vi sạch đã quan sát được, thay vì chỉ dựa vào baseline chung, vì heuristic quá rộng sẽ đổi precision lấy coverage rất nhanh.

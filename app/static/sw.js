self.addEventListener("push", function(event) {
  const data = event.data.json();
  const options = {
    body: data.body,
    icon: "/icon.png",   // ใช้ไฟล์ icon.png ที่อยู่ root
    data: { url: data.url || "https://winner-line-bot-app.onrender.com/chat_all" }
  };
  event.waitUntil(
    self.registration.showNotification(data.title, options)
  );
});

self.addEventListener("notificationclick", function(event) {
  event.notification.close();
  event.waitUntil(
    clients.openWindow(event.notification.data.url)
  );
});

"use client";

import { useState } from "react";
import { Button, Modal, Input, List, Space, Avatar, Typography } from "antd";
import {
  MessageOutlined,
  UserOutlined,
  CommentOutlined,
} from "@ant-design/icons";
import axios from "axios";

const { Text } = Typography;

interface Message {
  role: "user" | "agent";
  message: string;
}

const ChatWidget = () => {
  const [open, setOpen] = useState(false);
  const [chat, setChat] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [greeted, setGreeted] = useState(false);
  const [sessionId] = useState(() =>
    `sess_${Math.random().toString(36).slice(2, 10)}`
  );
  const [slots, setSlots] = useState<string[]>([]);
  const [awaitingSlot, setAwaitingSlot] = useState(false);

  const sendMessage = async (messageToSend: string) => {
    if (!messageToSend.trim()) return;

    const userMessage: Message = { role: "user", message: messageToSend };
    setChat((prev) => [...prev, userMessage]);
    setInput("");

    try {
      const res = await axios.post("http://127.0.0.1:8000/chat", {
        session_id: sessionId,
        message: messageToSend,
      });

      let agentMessageText = "";
      let extractedSlots: string[] = [];

      if (typeof res.data.response === "string") {
        agentMessageText = res.data.response;
      } else if (typeof res.data.response === "object") {
        agentMessageText =
          res.data.response.text || "Here are the available slots:";
        extractedSlots = Array.isArray(res.data.response.slots)
          ? res.data.response.slots
          : [];
      }

      const agentMessage: Message = { role: "agent", message: agentMessageText };
      setChat((prev) => [...prev, agentMessage]);

      if (extractedSlots.length > 0) {
        setSlots(extractedSlots);
        setAwaitingSlot(true);
      } else {
        setSlots([]);
        setAwaitingSlot(false);
      }
    } catch (err) {
      console.error("Error:", err);
    }
  };

  const handleOpen = async () => {
    setOpen(true);
    if (!greeted) {
      try {
        const res = await axios.post("http://127.0.0.1:8000/chat", {
          session_id: sessionId,
          message: "",
        });

        let greetingMessage = "";
        if (typeof res.data.response === "string") {
          greetingMessage = res.data.response;
        } else if (typeof res.data.response === "object") {
          greetingMessage = res.data.response.text || "Hi! How can I help you today?";
        }

        setChat([{ role: "agent", message: greetingMessage }]);
        setGreeted(true);
      } catch (err) {
        console.error("Greeting failed:", err);
      }
    }
  };

  const handleSlotClick = (slot: string) => {
    setSlots([]);
    setAwaitingSlot(false);
    sendMessage(slot);
  };

  return (
    <>
      <Button
        type="primary"
        shape="circle"
        icon={<MessageOutlined />}
        size="large"
        style={{ position: "fixed", bottom: 24, right: 24, zIndex: 1000 }}
        onClick={handleOpen}
      />
      <Modal
        open={open}
        title="Amenity Booking Assistant 🤖"
        onCancel={() => setOpen(false)}
        footer={null}
      >
        <List
          dataSource={chat}
          renderItem={(item: Message, index) => (
            <List.Item
              key={index}
              style={{
                justifyContent: item.role === "user" ? "flex-end" : "flex-start",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", maxWidth: "75%" }}>
                {item.role === "agent" && (
                  <Avatar
                    icon={<CommentOutlined />}
                    style={{
                      backgroundColor: "#ccc",
                      marginRight: 8,
                    }}
                  />
                )}
                <div
                  style={{
                    background: item.role === "user" ? "#1890ff" : "#f0f0f0",
                    color: item.role === "user" ? "#fff" : "#000",
                    padding: "8px 12px",
                    borderRadius: 8,
                  }}
                >
                  {item.message}
                </div>
                {item.role === "user" && (
                  <Avatar
                    icon={<UserOutlined />}
                    style={{
                      backgroundColor: "#1890ff",
                      marginLeft: 8,
                    }}
                  />
                )}
              </div>
            </List.Item>
          )}
        />

        {awaitingSlot && (
          <div style={{ marginTop: 16 }}>
            <Text strong>Select a time slot:</Text>
            <List
              size="small"
              dataSource={slots}
              renderItem={(slot, idx) => (
                <List.Item key={idx}>
                  <Button block onClick={() => handleSlotClick(slot)}>
                    {slot}
                  </Button>
                </List.Item>
              )}
            />
          </div>
        )}

        {!awaitingSlot && (
          <Input.Search
            placeholder="Type your message..."
            enterButton="Send"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onSearch={() => sendMessage(input)}
            style={{ marginTop: 12 }}
          />
        )}
      </Modal>
    </>
  );
};

export default ChatWidget;

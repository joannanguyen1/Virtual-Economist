import React, { useState } from 'react';

interface ChatInputProps {
  onSendMessage: (message: string) => void;
}

const ChatInput: React.FC<ChatInputProps> = ({ onSendMessage }) => {
  const [inputValue, setInputValue] = useState('');

  const handleChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setInputValue(event.target.value);
  };

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    if (inputValue.trim() !== '') {
      onSendMessage(inputValue);
      setInputValue('');
    }
  };

  return (
    <form onSubmit={handleSubmit} className="input-wrapper">
      <input
        type="text"
        value={inputValue}
        onChange={handleChange}
        placeholder="Type your message here..."
        className="chat-input"
        onKeyPress={(e) => e.key === 'Enter' && handleSubmit(e)}
      />
      <button type="submit" className="chat-submit">
        Send
      </button>
    </form>
  );
};

export default ChatInput;

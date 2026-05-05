import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import ChatPage from './experimental-chat/ChatPage.tsx';
import './index.css';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ChatPage />
  </StrictMode>,
);

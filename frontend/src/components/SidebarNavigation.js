import React from 'react';

const SidebarNavigation = () => {
  return (
    <nav
      className="flex flex-col p-4 bg-white rounded-2xl border border-custom-border shadow-sm"
      aria-label="Chat history"
    >
      <div className="flex justify-between items-center mb-4">
        <button
          className="text-custom-text-secondary focus:bg-custom-blue-hover hover:bg-custom-blue-hover h-10 w-10 rounded-lg p-2 focus:outline-none"
          aria-label="Close sidebar"
        >
          <svg
            width="24"
            height="24"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              d="M8 8L16 16M16 8L8 16"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
            />
          </svg>
        </button>
        <button
          className="text-custom-text-secondary focus:bg-custom-blue-hover hover:bg-custom-blue-hover h-10 w-10 rounded-lg p-2 focus:outline-none"
          aria-label="Search"
        >
          <svg
            width="24"
            height="24"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            <circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="2" />
            <line x1="16" y1="16" x2="20" y2="20" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
          </svg>
        </button>
        <button
          className="text-custom-text-secondary focus:bg-custom-blue-hover hover:bg-custom-blue-hover h-10 w-10 rounded-lg p-2 focus:outline-none"
          aria-label="New chat"
        >
          <svg
            width="24"
            height="24"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              d="M12 5v14M5 12h14"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
            />
          </svg>
        </button>
      </div>
      <div className="flex flex-col gap-2">
        <a
          className="flex items-center p-2 rounded-lg hover:bg-custom-blue-bg transition"
          href="#"
        >
          <span className="text-sm text-custom-text truncate">
            ChatGPT
          </span>
        </a>
        <a
          className="flex items-center p-2 rounded-lg hover:bg-custom-blue-bg transition"
          href="#"
        >
          <span className="text-sm text-custom-text truncate">
            Conversations
          </span>
        </a>
      </div>
    </nav>
  );
};

export default SidebarNavigation;

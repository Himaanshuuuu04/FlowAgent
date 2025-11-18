interface SignInScreenProps {
  onLogin: () => void;
}

export function SignInScreen({ onLogin }: SignInScreenProps) {
  return (
    <div className="app">
      <header>
        <h1>🤖 AI Assistant</h1>
      </header>
      <section style={{ textAlign: "center", padding: "30px 16px" }}>
        <h3 style={{ fontSize: "16px", marginBottom: "10px" }}>
          Sign in Required
        </h3>
        <p style={{ color: "#666", marginBottom: "20px" }}>
          Please sign in with Google to use the AI assistant.
        </p>
        <button
          onClick={onLogin}
          style={{
            background: "#4285f4",
            color: "white",
            padding: "10px 20px",
            fontSize: "14px",
          }}
        >
          Sign in with Google
        </button>
      </section>
    </div>
  );
}

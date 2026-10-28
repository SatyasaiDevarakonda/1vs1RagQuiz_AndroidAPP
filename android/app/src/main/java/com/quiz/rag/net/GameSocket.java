package com.quiz.rag.net;

import android.os.Handler;
import android.os.Looper;

import org.json.JSONObject;

import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.TimeUnit;

import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.Response;
import okhttp3.WebSocket;
import okhttp3.WebSocketListener;
import okio.ByteString;

/**
 * Singleton WebSocket client matching the real backend's /ws protocol:
 * every message is {"event": "...", "data": {...}} in both directions.
 * The connection is kept alive across Lobby -> Quiz -> Result so the
 * server-authoritative game state is never interrupted.
 */
public class GameSocket {

    public interface Listener {
        void onEvent(String event, JSONObject data);
        void onSocketClosed();
    }

    private static GameSocket instance;

    private final OkHttpClient client;
    private WebSocket webSocket;
    private Listener listener;
    private final Handler mainHandler = new Handler(Looper.getMainLooper());

    private String mySocketId;
    private String currentRoomCode;
    private boolean connected = false;

    private GameSocket() {
        client = new OkHttpClient.Builder()
                .readTimeout(0, TimeUnit.MILLISECONDS) // WebSockets stay open indefinitely
                .pingInterval(20, TimeUnit.SECONDS)
                .build();
    }

    public static synchronized GameSocket get() {
        if (instance == null) instance = new GameSocket();
        return instance;
    }

    public void setListener(Listener listener) {
        this.listener = listener;
    }

    public boolean isConnected() {
        return connected && webSocket != null;
    }

    public String getMySocketId() {
        return mySocketId;
    }

    public String getCurrentRoomCode() {
        return currentRoomCode;
    }

    public void setCurrentRoomCode(String code) {
        this.currentRoomCode = code;
    }

    /** Opens a fresh connection. Closes any previous one first. */
    public void connect(String wsUrl) {
        close();

        Request request = new Request.Builder().url(wsUrl).build();
        webSocket = client.newWebSocket(request, new WebSocketListener() {
            @Override
            public void onOpen(WebSocket ws, Response response) {
                connected = true;
            }

            @Override
            public void onMessage(WebSocket ws, String text) {
                handleMessage(text);
            }

            @Override
            public void onMessage(WebSocket ws, ByteString bytes) {
                handleMessage(bytes.utf8());
            }

            @Override
            public void onClosed(WebSocket ws, int code, String reason) {
                connected = false;
                mySocketId = null;
                mainHandler.post(() -> {
                    if (listener != null) listener.onSocketClosed();
                });
            }

            @Override
            public void onFailure(WebSocket ws, Throwable t, Response response) {
                connected = false;
                mainHandler.post(() -> {
                    if (listener != null) listener.onSocketClosed();
                });
            }
        });
    }

    private void handleMessage(String text) {
        try {
            JSONObject json = new JSONObject(text);
            String event = json.optString("event", "");
            JSONObject data = json.optJSONObject("data");
            if (data == null) data = new JSONObject();

            if ("connected".equals(event)) {
                mySocketId = data.optString("socketId", null);
            }

            final String fEvent = event;
            final JSONObject fData = data;
            mainHandler.post(() -> {
                if (listener != null) listener.onEvent(fEvent, fData);
            });
        } catch (Exception ignored) {
            // Malformed frame - ignore
        }
    }

    /** Sends {"event": event, "data": data} to the server. */
    public void send(String event, Map<String, Object> data) {
        if (webSocket == null) return;
        try {
            JSONObject payload = new JSONObject();
            payload.put("event", event);
            payload.put("data", new JSONObject(data == null ? new HashMap<>() : data));
            webSocket.send(payload.toString());
        } catch (Exception ignored) {
        }
    }

    public void close() {
        if (webSocket != null) {
            webSocket.close(1000, "closing");
            webSocket = null;
        }
        connected = false;
        mySocketId = null;
        currentRoomCode = null;
    }
}

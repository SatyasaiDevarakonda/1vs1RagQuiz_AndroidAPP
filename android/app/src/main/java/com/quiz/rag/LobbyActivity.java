package com.quiz.rag;

import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Context;
import android.content.Intent;
import android.os.Bundle;
import android.view.View;
import android.widget.Button;
import android.widget.ImageView;
import android.widget.TextView;
import android.widget.Toast;

import androidx.appcompat.app.AppCompatActivity;

import com.quiz.rag.net.ApiClient;
import com.quiz.rag.net.GameSocket;

import org.json.JSONArray;
import org.json.JSONObject;

import java.util.HashMap;
import java.util.Map;

/**
 * Owns the actual WebSocket handshake with the real backend's /ws endpoint:
 * create_room or join_room -> player_joined -> toggle_ready -> countdown -> game_started.
 * The socket is kept open and handed off to QuizActivity, it is never closed here.
 *
 * Three modes:
 *  - "solo": single-player, no lobby wait - the backend starts the quiz immediately.
 *  - "create": host a 1v1 room and wait for an opponent.
 *  - "join": join an existing 1v1 room by its code.
 */
public class LobbyActivity extends AppCompatActivity implements GameSocket.Listener {

    private TextView tvRoomCode, tvPlayer1Name, tvPlayer1Status, tvPlayer2Name, tvPlayer2Status, tvLobbyStatus;
    private ImageView ivPlayer1Avatar, ivPlayer2Avatar;
    private Button btnCopyCode, btnInviteSms, btnStartBattle;
    private View cardRoomCode, cardPlayers;

    private String mode; // "solo", "create" or "join"
    private String roomCode;
    private String sourceDocument;
    private String myUsername;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_lobby);

        mode = getIntent().getStringExtra("mode");
        if (mode == null) mode = "create";
        roomCode = getIntent().getStringExtra("roomCode");

        myUsername = getSharedPreferences("rag_prefs", MODE_PRIVATE).getString("username", "You");

        tvRoomCode = findViewById(R.id.tvRoomCode);
        tvPlayer1Name = findViewById(R.id.tvPlayer1Name);
        tvPlayer1Status = findViewById(R.id.tvPlayer1Status);
        tvPlayer2Name = findViewById(R.id.tvPlayer2Name);
        tvPlayer2Status = findViewById(R.id.tvPlayer2Status);
        tvLobbyStatus = findViewById(R.id.tvLobbyStatus);
        ivPlayer1Avatar = findViewById(R.id.ivPlayer1Avatar);
        ivPlayer2Avatar = findViewById(R.id.ivPlayer2Avatar);
        btnCopyCode = findViewById(R.id.btnCopyCode);
        btnInviteSms = findViewById(R.id.btnInviteSms);
        btnStartBattle = findViewById(R.id.btnStartBattle);
        cardRoomCode = findViewById(R.id.cardRoomCode);
        cardPlayers = findViewById(R.id.cardPlayers);

        tvPlayer1Name.setText(myUsername);

        if ("solo".equals(mode)) {
            cardRoomCode.setVisibility(View.GONE);
            cardPlayers.setVisibility(View.GONE);
            btnStartBattle.setVisibility(View.GONE);
            tvLobbyStatus.setText(getString(R.string.preparing_quiz));
        } else {
            tvRoomCode.setText(roomCode != null ? roomCode : "----");
            tvLobbyStatus.setText("Connecting…");
            btnStartBattle.setText("Waiting for opponent…");
            btnStartBattle.setEnabled(false);

            btnCopyCode.setOnClickListener(v -> {
                if (roomCode == null) return;
                ClipboardManager cm = (ClipboardManager) getSystemService(Context.CLIPBOARD_SERVICE);
                cm.setPrimaryClip(ClipData.newPlainText("Room code", roomCode));
                Toast.makeText(this, "Room code " + roomCode + " copied", Toast.LENGTH_SHORT).show();
            });

            btnInviteSms.setOnClickListener(v -> {
                if (roomCode == null) return;
                Intent share = new Intent(Intent.ACTION_SEND);
                share.setType("text/plain");
                share.putExtra(Intent.EXTRA_TEXT, "Join my quiz match! Room code: " + roomCode);
                startActivity(Intent.createChooser(share, "Share room code via"));
            });

            btnStartBattle.setOnClickListener(v -> toggleReady());
        }

        GameSocket.get().setListener(this);
        GameSocket.get().connect(ApiClient.getWsUrl(this));
    }

    private void toggleReady() {
        Map<String, Object> data = new HashMap<>();
        data.put("roomCode", roomCode);
        GameSocket.get().send("toggle_ready", data);
    }

    @Override
    public void onEvent(String event, JSONObject data) {
        switch (event) {
            case "connected":
                onSocketConnected();
                break;
            case "room_created":
                roomCode = data.optString("roomCode", roomCode);
                GameSocket.get().setCurrentRoomCode(roomCode);
                tvRoomCode.setText(roomCode);
                tvLobbyStatus.setText("Share this code - waiting for an opponent to join…");
                btnStartBattle.setText("Waiting for opponent…");
                break;
            case "room_joined":
                roomCode = data.optString("roomCode", roomCode);
                GameSocket.get().setCurrentRoomCode(roomCode);
                tvRoomCode.setText(roomCode);
                renderPlayers(data.optJSONArray("players"));
                btnStartBattle.setEnabled(true);
                btnStartBattle.setText(getString(R.string.btn_ready));
                tvLobbyStatus.setText("Connected. Tap ready when you're set.");
                break;
            case "player_joined":
            case "player_ready_changed":
            case "player_disconnected":
                renderPlayers(data.optJSONArray("players"));
                break;
            case "countdown_started":
                tvLobbyStatus.setText("Starting in " + data.optInt("countdown", 3) + "…");
                break;
            case "countdown_tick":
                int left = data.optInt("countdown", 0);
                tvLobbyStatus.setText(left > 0 ? ("Starting in " + left + "…") : "Go!");
                break;
            case "game_started":
                sourceDocument = data.isNull("sourceDocument") ? null : data.optString("sourceDocument", null);
                launchQuizActivity();
                break;
            case "error":
                Toast.makeText(this, data.optString("message", "Something went wrong"), Toast.LENGTH_LONG).show();
                break;
            default:
                break;
        }
    }

    private void onSocketConnected() {
        // "join" is an explicit 1v1 join-by-code. A "solo" room that already
        // has a roomCode came from the PDF-upload flow (the REST call already
        // created it) - the host still has to join_room, same as any room
        // that exists before its creator connects over the socket.
        if ("join".equals(mode) || ("solo".equals(mode) && roomCode != null)) {
            Map<String, Object> data = new HashMap<>();
            data.put("token", getToken());
            data.put("username", myUsername);
            data.put("roomCode", roomCode);
            GameSocket.get().send("join_room", data);
        } else {
            Map<String, Object> data = new HashMap<>();
            data.put("token", getToken());
            data.put("username", myUsername);
            data.put("mode", "solo".equals(mode) ? "single" : "multiplayer");
            Map<String, Object> settings = new HashMap<>();
            settings.put("questionsCount", 5);
            settings.put("timePerQuestion", 15);
            data.put("settings", settings);
            GameSocket.get().send("create_room", data);
        }
    }

    private void renderPlayers(JSONArray players) {
        if (players == null) return;
        String mySocketId = GameSocket.get().getMySocketId();

        for (int i = 0; i < players.length(); i++) {
            JSONObject p = players.optJSONObject(i);
            if (p == null) continue;
            boolean isMe = p.optString("socketId", "").equals(mySocketId);
            String username = p.optString("username", "Player");
            boolean ready = p.optBoolean("isReady", false);

            if (isMe) {
                tvPlayer1Name.setText(username);
                tvPlayer1Status.setText(ready ? "Ready" : "Not ready");
                tvPlayer1Status.setTextColor(getResources().getColor(ready ? R.color.success : R.color.text_muted));
                btnStartBattle.setText(ready ? "Waiting for opponent…" : getString(R.string.btn_ready));
            } else {
                ivPlayer2Avatar.setAlpha(1f);
                tvPlayer2Name.setText(username);
                tvPlayer2Status.setText(ready ? "Ready" : "Not ready");
                tvPlayer2Status.setTextColor(getResources().getColor(ready ? R.color.success : R.color.warning));
            }
        }

        if (players.length() < 2) {
            ivPlayer2Avatar.setAlpha(0.35f);
            tvPlayer2Name.setText("Waiting…");
            tvPlayer2Status.setText("No one yet");
            tvPlayer2Status.setTextColor(getResources().getColor(R.color.text_muted));
        }
    }

    private String getToken() {
        return getSharedPreferences("rag_prefs", MODE_PRIVATE).getString("token", "");
    }

    private void launchQuizActivity() {
        Intent intent = new Intent(LobbyActivity.this, QuizActivity.class);
        intent.putExtra("roomCode", roomCode);
        intent.putExtra("sourceDocument", sourceDocument);
        startActivity(intent);
        finish();
    }

    @Override
    public void onSocketClosed() {
        Toast.makeText(this, "Lost connection to the server", Toast.LENGTH_LONG).show();
    }
}

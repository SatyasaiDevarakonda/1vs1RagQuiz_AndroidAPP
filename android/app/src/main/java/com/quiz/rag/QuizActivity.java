package com.quiz.rag;

import android.content.Intent;
import android.os.Bundle;
import android.view.View;
import android.widget.Button;
import android.widget.TextView;
import android.widget.Toast;

import androidx.appcompat.app.AppCompatActivity;

import com.quiz.rag.net.GameSocket;

import org.json.JSONArray;
import org.json.JSONObject;

import java.util.HashMap;
import java.util.Map;

/**
 * Server-authoritative 1v1 quiz screen. Every question, timer tick and score
 * update comes from the backend's WebSocket broadcasts - this activity never
 * decides timing or correctness locally, it just renders what the server says.
 * Answering is click-only: tap an option to submit it immediately.
 */
public class QuizActivity extends AppCompatActivity implements GameSocket.Listener {

    private String roomCode;
    private String myUsername;
    private boolean answeredThisRound = false;
    private int selectedIndex = -1;

    private TextView tvMyName, tvMyScore, tvOpponentName, tvOpponentScore, tvTimer, tvQuestionProgress, tvQuestion, tvSourceDocument;
    private Button btnOption0, btnOption1, btnOption2, btnOption3;
    private Button[] optionButtons;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_quiz);

        roomCode = getIntent().getStringExtra("roomCode");
        String sourceDocument = getIntent().getStringExtra("sourceDocument");
        myUsername = getSharedPreferences("rag_prefs", MODE_PRIVATE).getString("username", "You");

        tvMyName = findViewById(R.id.tvMyName);
        tvMyScore = findViewById(R.id.tvMyScore);
        tvOpponentName = findViewById(R.id.tvOpponentName);
        tvOpponentScore = findViewById(R.id.tvOpponentScore);
        tvTimer = findViewById(R.id.tvTimer);
        tvQuestionProgress = findViewById(R.id.tvQuestionProgress);
        tvQuestion = findViewById(R.id.tvQuestion);
        tvSourceDocument = findViewById(R.id.tvSourceDocument);

        if (sourceDocument != null) {
            tvSourceDocument.setText("Source: " + sourceDocument);
            tvSourceDocument.setVisibility(View.VISIBLE);
        }

        btnOption0 = findViewById(R.id.btnOption0);
        btnOption1 = findViewById(R.id.btnOption1);
        btnOption2 = findViewById(R.id.btnOption2);
        btnOption3 = findViewById(R.id.btnOption3);
        optionButtons = new Button[]{btnOption0, btnOption1, btnOption2, btnOption3};

        tvMyName.setText(myUsername);

        for (int i = 0; i < optionButtons.length; i++) {
            int index = i;
            optionButtons[i].setOnClickListener(v -> selectOption(index));
        }

        GameSocket.get().setListener(this);
    }

    private void selectOption(int index) {
        if (answeredThisRound) return;
        answeredThisRound = true;
        selectedIndex = index;

        // Immediate feedback so the tap is clearly "recorded" even before the
        // server confirms - the real correct/incorrect state arrives in answer_result.
        optionButtons[index].setBackgroundResource(R.drawable.bg_option_selected);
        setOptionsEnabled(false);

        Map<String, Object> data = new HashMap<>();
        data.put("roomCode", roomCode);
        data.put("answer", optionButtons[index].getText().toString());
        GameSocket.get().send("submit_answer", data);
    }

    private void setOptionsEnabled(boolean enabled) {
        for (Button b : optionButtons) b.setEnabled(enabled);
    }

    private void resetOptionBackgrounds() {
        for (Button b : optionButtons) b.setBackgroundResource(R.drawable.bg_option_default);
    }

    @Override
    public void onEvent(String event, JSONObject data) {
        switch (event) {
            case "question":
                renderQuestion(data);
                break;
            case "time_update":
                tvTimer.setText(String.valueOf(data.optInt("timeLeft", 0)));
                break;
            case "answer_accepted":
                break;
            case "answer_result":
                renderAnswerResult(data);
                break;
            case "scores_update":
                updateScores(data.optJSONArray("players"));
                break;
            case "game_ended":
                goToResults(data);
                break;
            case "error":
                Toast.makeText(this, data.optString("message", "Something went wrong"), Toast.LENGTH_LONG).show();
                break;
            default:
                break;
        }
    }

    private void renderQuestion(JSONObject data) {
        answeredThisRound = false;
        selectedIndex = -1;
        resetOptionBackgrounds();
        setOptionsEnabled(true);

        int idx = data.optInt("questionIndex", 0);
        int total = data.optInt("totalQuestions", 1);
        tvQuestionProgress.setText("Question " + (idx + 1) + " of " + total);
        tvQuestion.setText(data.optString("question", ""));
        tvTimer.setText(String.valueOf(data.optInt("timeLimit", 15)));

        JSONArray options = data.optJSONArray("options");
        for (int i = 0; i < optionButtons.length; i++) {
            String opt = (options != null && i < options.length()) ? options.optString(i, "") : "";
            optionButtons[i].setText(opt);
            optionButtons[i].setVisibility(opt.isEmpty() ? View.GONE : View.VISIBLE);
        }
    }

    private void renderAnswerResult(JSONObject data) {
        boolean correct = data.optBoolean("correct", false);
        boolean timedOut = data.optBoolean("timedOut", false);
        String correctAnswer = data.optString("correctAnswer", "");
        tvMyScore.setText(data.optInt("score", 0) + " pts");

        for (Button b : optionButtons) {
            String text = b.getText().toString();
            if (text.equals(correctAnswer)) {
                b.setBackgroundResource(R.drawable.bg_option_correct);
            } else if (!timedOut && !correct && selectedIndex >= 0 && b == optionButtons[selectedIndex]) {
                b.setBackgroundResource(R.drawable.bg_option_wrong);
            }
        }

        if (timedOut) {
            Toast.makeText(this, "Time's up", Toast.LENGTH_SHORT).show();
        } else if (correct) {
            Toast.makeText(this, "Correct! +" + data.optInt("pointsEarned", 0) + " pts", Toast.LENGTH_SHORT).show();
        }
    }

    private void updateScores(JSONArray players) {
        if (players == null) return;
        String mySocketId = GameSocket.get().getMySocketId();

        for (int i = 0; i < players.length(); i++) {
            JSONObject p = players.optJSONObject(i);
            if (p == null) continue;
            boolean isMe = p.optString("socketId", "").equals(mySocketId);
            if (isMe) {
                tvMyScore.setText(p.optInt("score", 0) + " pts");
            } else {
                tvOpponentName.setText(p.optString("username", "Opponent"));
                tvOpponentScore.setText(p.optInt("score", 0) + " pts");
            }
        }
    }

    private void goToResults(JSONObject data) {
        Intent intent = new Intent(QuizActivity.this, ResultActivity.class);
        intent.putExtra("resultJson", data.toString());
        startActivity(intent);
        finish();
    }

    @Override
    public void onSocketClosed() {
        Toast.makeText(this, "Connection to the server was lost", Toast.LENGTH_LONG).show();
    }
}

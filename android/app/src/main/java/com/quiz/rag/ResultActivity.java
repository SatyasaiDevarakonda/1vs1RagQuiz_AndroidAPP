package com.quiz.rag;

import android.content.Intent;
import android.os.Bundle;
import android.widget.Button;
import android.widget.TextView;

import androidx.appcompat.app.AppCompatActivity;

import org.json.JSONArray;
import org.json.JSONObject;

/**
 * Renders the final "game_ended" WebSocket payload handed off from QuizActivity.
 * No REST call - the server already sent everything we need.
 */
public class ResultActivity extends AppCompatActivity {

    private TextView tvWinnerStatus, tvWinnerText, tvResultSource, tvSummaryScores;
    private Button btnPlayAgain, btnBackHome;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_result);

        tvWinnerStatus = findViewById(R.id.tvWinnerStatus);
        tvWinnerText = findViewById(R.id.tvWinnerText);
        tvResultSource = findViewById(R.id.tvResultSource);
        tvSummaryScores = findViewById(R.id.tvSummaryScores);
        btnPlayAgain = findViewById(R.id.btnPlayAgain);
        btnBackHome = findViewById(R.id.btnBackHome);

        btnPlayAgain.setOnClickListener(v -> {
            Intent intent = new Intent(ResultActivity.this, MainActivity.class);
            intent.putExtra("openTab", "play");
            startActivity(intent);
            finish();
        });

        btnBackHome.setOnClickListener(v -> {
            startActivity(new Intent(ResultActivity.this, MainActivity.class));
            finish();
        });

        renderResult();
    }

    private void renderResult() {
        String myName = getSharedPreferences("rag_prefs", MODE_PRIVATE).getString("username", "You");
        String json = getIntent().getStringExtra("resultJson");

        if (json == null) {
            tvSummaryScores.setText("Match completed.");
            return;
        }

        try {
            JSONObject result = new JSONObject(json);
            String winner = result.isNull("winner") ? null : result.optString("winner", null);
            JSONArray players = result.optJSONArray("players");

            if (winner == null) {
                tvWinnerStatus.setText("Match complete");
                tvWinnerText.setText("Thanks for playing!");
            } else if ("draw".equals(winner)) {
                tvWinnerStatus.setText("It's a tie");
                tvWinnerText.setText("Both players scored equally.");
            } else if (myName.equalsIgnoreCase(winner)) {
                tvWinnerStatus.setText("You won");
                tvWinnerText.setText("Nice work on this round.");
            } else {
                tvWinnerStatus.setText("You lost");
                tvWinnerText.setText(winner + " took this round.");
            }

            String sourceDocument = result.isNull("sourceDocument") ? null : result.optString("sourceDocument", null);
            if (sourceDocument != null) {
                tvResultSource.setText("Source: " + sourceDocument);
                tvResultSource.setVisibility(android.view.View.VISIBLE);
            }

            if (players != null) {
                StringBuilder sb = new StringBuilder();
                for (int i = 0; i < players.length(); i++) {
                    JSONObject p = players.optJSONObject(i);
                    if (p == null) continue;
                    String username = p.optString("username", "Player");
                    int score = p.optInt("score", 0);
                    int correct = p.optInt("correctAnswers", 0);
                    sb.append("• ").append(username).append(": ")
                            .append(score).append(" pts (")
                            .append(correct).append(" correct)\n");
                }
                tvSummaryScores.setText(sb.toString().trim());
            }
        } catch (Exception e) {
            tvSummaryScores.setText("Match completed.");
        }
    }
}

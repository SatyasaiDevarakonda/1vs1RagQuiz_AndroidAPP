package com.quiz.rag;

import android.os.Bundle;
import android.widget.TextView;

import androidx.appcompat.app.AppCompatActivity;
import androidx.recyclerview.widget.LinearLayoutManager;
import androidx.recyclerview.widget.RecyclerView;

import com.quiz.rag.adapter.QuestionResultAdapter;

import org.json.JSONArray;
import org.json.JSONObject;

/**
 * Full breakdown of one past match, from the "historyJson" extra - a single
 * entry of GET /api/profile/history, including its per-question answer log.
 */
public class MatchDetailActivity extends AppCompatActivity {

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_match_detail);

        TextView tvBack = findViewById(R.id.tvBack);
        TextView tvTitle = findViewById(R.id.tvDetailTitle);
        TextView tvMeta = findViewById(R.id.tvDetailMeta);
        TextView tvSource = findViewById(R.id.tvDetailSource);
        TextView tvScore = findViewById(R.id.tvDetailScore);
        TextView tvNoLog = findViewById(R.id.tvNoLog);
        RecyclerView rvQuestionResults = findViewById(R.id.rvQuestionResults);

        tvBack.setOnClickListener(v -> finish());

        String json = getIntent().getStringExtra("historyJson");
        if (json == null) {
            finish();
            return;
        }

        try {
            JSONObject item = new JSONObject(json);

            String opponent = item.isNull("opponentUsername") ? null : item.optString("opponentUsername", null);
            tvTitle.setText(opponent != null ? "vs " + opponent : "Solo quiz");

            String result = item.optString("result", "completed");
            String mode = item.optString("mode", "");
            tvMeta.setText(mode + " • " + result.substring(0, 1).toUpperCase() + result.substring(1));

            String source = item.isNull("sourceDocument") ? null : item.optString("sourceDocument", null);
            if (source != null) {
                tvSource.setText("Source: " + source);
                tvSource.setVisibility(android.view.View.VISIBLE);
            }

            tvScore.setText(item.optInt("score", 0) + " pts  •  " +
                    item.optInt("correctAnswers", 0) + "/" + item.optInt("totalQuestions", 0) + " correct");

            JSONArray questionLog = item.optJSONArray("questionLog");
            if (questionLog == null || questionLog.length() == 0) {
                tvNoLog.setVisibility(android.view.View.VISIBLE);
            } else {
                rvQuestionResults.setLayoutManager(new LinearLayoutManager(this));
                rvQuestionResults.setAdapter(new QuestionResultAdapter(questionLog));
            }
        } catch (Exception e) {
            finish();
        }
    }
}

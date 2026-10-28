package com.quiz.rag.adapter;

import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.TextView;

import androidx.annotation.NonNull;
import androidx.recyclerview.widget.RecyclerView;

import com.quiz.rag.R;

import org.json.JSONArray;
import org.json.JSONObject;

/** Shows the per-question breakdown of a past match (question, your answer, correct answer). */
public class QuestionResultAdapter extends RecyclerView.Adapter<QuestionResultAdapter.ViewHolder> {

    private final JSONArray questionLog;

    public QuestionResultAdapter(JSONArray questionLog) {
        this.questionLog = questionLog;
    }

    @NonNull
    @Override
    public ViewHolder onCreateViewHolder(@NonNull ViewGroup parent, int viewType) {
        View view = LayoutInflater.from(parent.getContext()).inflate(R.layout.item_question_result, parent, false);
        return new ViewHolder(view);
    }

    @Override
    public void onBindViewHolder(@NonNull ViewHolder holder, int position) {
        JSONObject q = questionLog.optJSONObject(position);
        if (q == null) return;

        holder.tvQuestion.setText((position + 1) + ". " + q.optString("question", ""));

        boolean correct = q.optBoolean("correct", false);
        String yourAnswer = q.isNull("yourAnswer") ? null : q.optString("yourAnswer", null);
        String correctAnswer = q.optString("correctAnswer", "");

        if (yourAnswer == null) {
            holder.tvYourAnswer.setText("Your answer: no answer (time ran out)");
        } else {
            holder.tvYourAnswer.setText("Your answer: " + yourAnswer);
        }
        holder.tvCorrectAnswer.setText("Correct answer: " + correctAnswer);

        if (correct) {
            holder.tvBadge.setText("✓");
            holder.tvBadge.setBackgroundResource(R.drawable.bg_badge_win);
            holder.tvBadge.setTextColor(holder.tvBadge.getResources().getColor(R.color.success));
        } else {
            holder.tvBadge.setText("✕");
            holder.tvBadge.setBackgroundResource(R.drawable.bg_badge_loss);
            holder.tvBadge.setTextColor(holder.tvBadge.getResources().getColor(R.color.error));
        }
    }

    @Override
    public int getItemCount() {
        return questionLog == null ? 0 : questionLog.length();
    }

    public static class ViewHolder extends RecyclerView.ViewHolder {
        TextView tvBadge, tvQuestion, tvYourAnswer, tvCorrectAnswer;

        public ViewHolder(@NonNull View itemView) {
            super(itemView);
            tvBadge = itemView.findViewById(R.id.tvQResultBadge);
            tvQuestion = itemView.findViewById(R.id.tvQResultQuestion);
            tvYourAnswer = itemView.findViewById(R.id.tvQResultYourAnswer);
            tvCorrectAnswer = itemView.findViewById(R.id.tvQResultCorrectAnswer);
        }
    }
}

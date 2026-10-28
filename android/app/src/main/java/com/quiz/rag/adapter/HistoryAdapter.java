package com.quiz.rag.adapter;

import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.TextView;

import androidx.annotation.NonNull;
import androidx.recyclerview.widget.RecyclerView;

import com.quiz.rag.R;
import com.quiz.rag.model.GameHistoryItem;

import java.util.List;

public class HistoryAdapter extends RecyclerView.Adapter<HistoryAdapter.ViewHolder> {

    public interface OnItemClickListener {
        void onItemClick(GameHistoryItem item);
    }

    private final List<GameHistoryItem> items;
    private final OnItemClickListener listener;

    public HistoryAdapter(List<GameHistoryItem> items, OnItemClickListener listener) {
        this.items = items;
        this.listener = listener;
    }

    @NonNull
    @Override
    public ViewHolder onCreateViewHolder(@NonNull ViewGroup parent, int viewType) {
        View view = LayoutInflater.from(parent.getContext()).inflate(R.layout.item_history, parent, false);
        return new ViewHolder(view);
    }

    @Override
    public void onBindViewHolder(@NonNull ViewHolder holder, int position) {
        GameHistoryItem item = items.get(position);

        String title = item.getOpponentUsername() != null
                ? "vs " + item.getOpponentUsername()
                : "single".equals(item.getMode()) ? "Solo quiz" : "Solo";
        holder.tvOpponent.setText(title);

        String detail = item.getCorrectAnswers() + "/" + item.getTotalQuestions() + " correct";
        detail += item.getSourceDocument() != null ? " • " + item.getSourceDocument() : " • Room " + item.getRoomCode();
        holder.tvMeta.setText(detail);

        holder.tvScore.setText(item.getScore() + " pts");
        holder.itemView.setOnClickListener(v -> {
            if (listener != null) listener.onItemClick(item);
        });

        String result = item.getResult() == null ? "completed" : item.getResult();
        switch (result) {
            case "win":
                holder.tvBadge.setText("W");
                holder.tvBadge.setBackgroundResource(R.drawable.bg_badge_win);
                holder.tvBadge.setTextColor(holder.tvBadge.getResources().getColor(R.color.success));
                break;
            case "loss":
                holder.tvBadge.setText("L");
                holder.tvBadge.setBackgroundResource(R.drawable.bg_badge_loss);
                holder.tvBadge.setTextColor(holder.tvBadge.getResources().getColor(R.color.error));
                break;
            case "draw":
                holder.tvBadge.setText("D");
                holder.tvBadge.setBackgroundResource(R.drawable.bg_badge_neutral);
                holder.tvBadge.setTextColor(holder.tvBadge.getResources().getColor(R.color.text_secondary));
                break;
            default:
                holder.tvBadge.setText("•");
                holder.tvBadge.setBackgroundResource(R.drawable.bg_badge_neutral);
                holder.tvBadge.setTextColor(holder.tvBadge.getResources().getColor(R.color.text_secondary));
        }
    }

    @Override
    public int getItemCount() {
        return items.size();
    }

    public static class ViewHolder extends RecyclerView.ViewHolder {
        TextView tvBadge, tvOpponent, tvMeta, tvScore;

        public ViewHolder(@NonNull View itemView) {
            super(itemView);
            tvBadge = itemView.findViewById(R.id.tvHistoryBadge);
            tvOpponent = itemView.findViewById(R.id.tvHistoryOpponent);
            tvMeta = itemView.findViewById(R.id.tvHistoryMeta);
            tvScore = itemView.findViewById(R.id.tvHistoryScore);
        }
    }
}

package com.quiz.rag.fragments;

import android.content.Intent;
import android.os.Bundle;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.ProgressBar;
import android.widget.TextView;
import android.widget.Toast;

import androidx.annotation.NonNull;
import androidx.annotation.Nullable;
import androidx.fragment.app.Fragment;
import androidx.recyclerview.widget.LinearLayoutManager;
import androidx.recyclerview.widget.RecyclerView;
import androidx.swiperefreshlayout.widget.SwipeRefreshLayout;

import com.quiz.rag.MatchDetailActivity;
import com.quiz.rag.R;
import com.quiz.rag.adapter.HistoryAdapter;
import com.quiz.rag.model.GameHistoryItem;
import com.quiz.rag.net.ApiClient;

import org.json.JSONObject;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

import retrofit2.Call;
import retrofit2.Callback;
import retrofit2.Response;

/**
 * Shows the signed-in player's real match history from
 * GET /api/profile/history (guests have no persistent history).
 */
public class LeaderboardFragment extends Fragment {

    private SwipeRefreshLayout swipeRefresh;
    private RecyclerView rvHistory;
    private TextView tvEmpty;
    private ProgressBar progressBar;
    private final List<GameHistoryItem> items = new ArrayList<>();
    private HistoryAdapter adapter;

    @Nullable
    @Override
    public View onCreateView(@NonNull LayoutInflater inflater, @Nullable ViewGroup container, @Nullable Bundle savedInstanceState) {
        View v = inflater.inflate(R.layout.fragment_leaderboard, container, false);

        swipeRefresh = v.findViewById(R.id.swipeRefreshHistory);
        rvHistory = v.findViewById(R.id.rvLeaderboard);
        tvEmpty = v.findViewById(R.id.tvHistoryEmpty);
        progressBar = v.findViewById(R.id.progressHistory);
        rvHistory.setLayoutManager(new LinearLayoutManager(getContext()));
        adapter = new HistoryAdapter(items, this::openDetail);
        rvHistory.setAdapter(adapter);

        swipeRefresh.setColorSchemeResources(R.color.primary);
        swipeRefresh.setOnRefreshListener(this::loadHistory);

        loadHistory();

        return v;
    }

    private void openDetail(GameHistoryItem item) {
        if (item.getRawJson() == null || getContext() == null) return;
        Intent intent = new Intent(getContext(), MatchDetailActivity.class);
        intent.putExtra("historyJson", item.getRawJson());
        startActivity(intent);
    }

    @SuppressWarnings("unchecked")
    private void loadHistory() {
        if (!swipeRefresh.isRefreshing()) {
            progressBar.setVisibility(View.VISIBLE);
            tvEmpty.setVisibility(View.GONE);
        }

        String bearer = ApiClient.bearer(requireContext());

        ApiClient.get(requireContext()).history(bearer).enqueue(new Callback<Map<String, Object>>() {
            @Override
            public void onResponse(Call<Map<String, Object>> call, Response<Map<String, Object>> response) {
                items.clear();
                if (response.isSuccessful() && response.body() != null) {
                    try {
                        // Retrofit/Gson hands back a List<Map<..>> for the "history" field
                        List<Map<String, Object>> raw = (List<Map<String, Object>>) response.body().get("history");
                        if (raw != null) {
                            for (Map<String, Object> h : raw) {
                                Object opp = h.get("opponentUsername");
                                Object oppScore = h.get("opponentScore");
                                Object sourceDoc = h.get("sourceDocument");
                                items.add(new GameHistoryItem(
                                        String.valueOf(h.get("roomCode")),
                                        String.valueOf(h.get("mode")),
                                        toInt(h.get("score")),
                                        toInt(h.get("totalQuestions")),
                                        toInt(h.get("correctAnswers")),
                                        opp == null ? null : String.valueOf(opp),
                                        oppScore == null ? null : toInt(oppScore),
                                        String.valueOf(h.get("result")),
                                        String.valueOf(h.get("playedAt")),
                                        sourceDoc == null ? null : String.valueOf(sourceDoc),
                                        new JSONObject(h).toString()
                                ));
                            }
                        }
                    } catch (Exception ignored) {
                    }
                }
                progressBar.setVisibility(View.GONE);
                swipeRefresh.setRefreshing(false);
                adapter.notifyDataSetChanged();
                tvEmpty.setVisibility(items.isEmpty() ? View.VISIBLE : View.GONE);
            }

            @Override
            public void onFailure(Call<Map<String, Object>> call, Throwable t) {
                progressBar.setVisibility(View.GONE);
                swipeRefresh.setRefreshing(false);
                if (getContext() != null) {
                    Toast.makeText(getContext(), "Could not reach server for history", Toast.LENGTH_SHORT).show();
                }
                tvEmpty.setVisibility(items.isEmpty() ? View.VISIBLE : View.GONE);
            }
        });
    }

    private static int toInt(Object o) {
        if (o == null) return 0;
        if (o instanceof Number) return ((Number) o).intValue();
        try {
            return (int) Double.parseDouble(String.valueOf(o));
        } catch (Exception e) {
            return 0;
        }
    }
}

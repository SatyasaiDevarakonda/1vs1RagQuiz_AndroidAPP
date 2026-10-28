package com.quiz.rag.fragments;

import android.content.Context;
import android.content.SharedPreferences;
import android.os.Bundle;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.TextView;

import androidx.annotation.NonNull;
import androidx.annotation.Nullable;
import androidx.fragment.app.Fragment;

import com.quiz.rag.MainActivity;
import com.quiz.rag.R;

public class HomeFragment extends Fragment {

    private TextView tvWelcome;
    private Button btnQuickBattle, btnHomeMatch;

    @Nullable
    @Override
    public View onCreateView(@NonNull LayoutInflater inflater, @Nullable ViewGroup container, @Nullable Bundle savedInstanceState) {
        View v = inflater.inflate(R.layout.fragment_home, container, false);

        tvWelcome = v.findViewById(R.id.tvWelcomeUser);
        btnQuickBattle = v.findViewById(R.id.btnQuickBattle);
        btnHomeMatch = v.findViewById(R.id.btnHomeMatch);

        SharedPreferences prefs = requireContext().getSharedPreferences("rag_prefs", Context.MODE_PRIVATE);
        String username = prefs.getString("username", "there");
        tvWelcome.setText("Welcome, " + username);

        // Starting a quiz always needs a document first - that selection UI
        // lives on the Play tab, so both buttons just take you there.
        btnQuickBattle.setOnClickListener(view -> openPlayTab());
        btnHomeMatch.setOnClickListener(view -> openPlayTab());

        return v;
    }

    private void openPlayTab() {
        if (getActivity() instanceof MainActivity) {
            ((MainActivity) getActivity()).openPlayTab();
        }
    }
}

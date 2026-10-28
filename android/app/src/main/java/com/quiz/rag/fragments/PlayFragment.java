package com.quiz.rag.fragments;

import android.content.Intent;
import android.database.Cursor;
import android.net.Uri;
import android.os.Bundle;
import android.provider.OpenableColumns;
import android.text.TextUtils;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.AdapterView;
import android.widget.Button;
import android.widget.EditText;
import android.widget.Spinner;
import android.widget.TextView;
import android.widget.Toast;

import androidx.activity.result.ActivityResultLauncher;
import androidx.activity.result.contract.ActivityResultContracts;
import androidx.annotation.NonNull;
import androidx.annotation.Nullable;
import androidx.fragment.app.Fragment;

import com.quiz.rag.LobbyActivity;
import com.quiz.rag.R;
import com.quiz.rag.net.ApiClient;

import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.util.Map;

import okhttp3.MediaType;
import okhttp3.MultipartBody;
import okhttp3.RequestBody;
import retrofit2.Call;
import retrofit2.Callback;
import retrofit2.Response;

/**
 * Battle hub. Starting a quiz - solo or 1v1 - always requires a document:
 * the questions are generated from it via the backend's RAG pipeline.
 * Joining an existing room by code needs no document (someone else already
 * created it). All hand off to LobbyActivity, which owns the WebSocket handshake.
 */
public class PlayFragment extends Fragment {

    private Button btnSolo, btnCreateRoom, btnJoinRoom, btnChooseFile;
    private EditText etJoinRoomCode;
    private TextView tvPdfFileName;
    private Spinner spQuestionCount, spTimePerQuestion, spDifficulty;
    private View pdfProgressRow;

    private Uri pickedFileUri;
    private String pickedFileName;

    private final ActivityResultLauncher<String[]> filePicker = registerForActivityResult(
            new ActivityResultContracts.OpenDocument(),
            uri -> {
                if (uri == null) return;
                pickedFileUri = uri;
                pickedFileName = resolveFileName(uri);
                tvPdfFileName.setText(pickedFileName != null ? pickedFileName : "Document selected");
                tvPdfFileName.setTextColor(getResources().getColor(R.color.text_primary));
            }
    );

    @Nullable
    @Override
    public View onCreateView(@NonNull LayoutInflater inflater, @Nullable ViewGroup container, @Nullable Bundle savedInstanceState) {
        View v = inflater.inflate(R.layout.fragment_play, container, false);

        btnSolo = v.findViewById(R.id.btnSolo);
        btnCreateRoom = v.findViewById(R.id.btnCreateRoom);
        etJoinRoomCode = v.findViewById(R.id.etJoinRoomCode);
        btnJoinRoom = v.findViewById(R.id.btnJoinRoom);
        btnChooseFile = v.findViewById(R.id.btnChooseFile);
        tvPdfFileName = v.findViewById(R.id.tvPdfFileName);
        spQuestionCount = v.findViewById(R.id.spQuestionCount);
        spTimePerQuestion = v.findViewById(R.id.spTimePerQuestion);
        spDifficulty = v.findViewById(R.id.spDifficulty);
        pdfProgressRow = v.findViewById(R.id.pdfProgressRow);

        btnChooseFile.setOnClickListener(view -> filePicker.launch(new String[]{
                "application/pdf",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "text/plain"
        }));
        btnSolo.setOnClickListener(view -> createRoomFromPdf("single"));
        btnCreateRoom.setOnClickListener(view -> createRoomFromPdf("multiplayer"));
        btnJoinRoom.setOnClickListener(view -> joinRoomByCode());

        return v;
    }

    private void joinRoomByCode() {
        String code = etJoinRoomCode.getText().toString().trim();
        if (TextUtils.isEmpty(code) || code.length() < 4) {
            etJoinRoomCode.setError("Enter the 4-digit room code");
            return;
        }

        Intent intent = new Intent(getActivity(), LobbyActivity.class);
        intent.putExtra("mode", "join");
        intent.putExtra("roomCode", code);
        startActivity(intent);
    }

    private String resolveFileName(Uri uri) {
        try (Cursor cursor = requireContext().getContentResolver().query(uri, null, null, null, null)) {
            if (cursor != null && cursor.moveToFirst()) {
                int idx = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME);
                if (idx >= 0) return cursor.getString(idx);
            }
        } catch (Exception ignored) {
        }
        return null;
    }

    @SuppressWarnings("unchecked")
    private void createRoomFromPdf(String mode) {
        if (pickedFileUri == null) {
            Toast.makeText(getContext(), "Choose a document first", Toast.LENGTH_SHORT).show();
            return;
        }

        File tempFile = copyUriToTempFile(pickedFileUri, pickedFileName);
        if (tempFile == null) {
            Toast.makeText(getContext(), "Could not read the selected file", Toast.LENGTH_SHORT).show();
            return;
        }

        setUploading(true);

        String[] questionCounts = getResources().getStringArray(R.array.pdf_question_count_values);
        String[] timesPerQuestion = getResources().getStringArray(R.array.pdf_time_per_question_values);
        String[] difficulties = getResources().getStringArray(R.array.pdf_difficulty_values);

        String questionsCount = questionCounts[spQuestionCount.getSelectedItemPosition()];
        String timePerQuestion = timesPerQuestion[spTimePerQuestion.getSelectedItemPosition()];
        String difficulty = difficulties[spDifficulty.getSelectedItemPosition()];

        MediaType mediaType = MediaType.parse(guessMimeType(tempFile.getName()));
        RequestBody fileBody = RequestBody.create(tempFile, mediaType);
        MultipartBody.Part filePart = MultipartBody.Part.createFormData("file", tempFile.getName(), fileBody);

        RequestBody questionsCountPart = RequestBody.create(questionsCount, MediaType.parse("text/plain"));
        RequestBody timePerQuestionPart = RequestBody.create(timePerQuestion, MediaType.parse("text/plain"));
        RequestBody difficultyPart = RequestBody.create(difficulty, MediaType.parse("text/plain"));
        RequestBody modePart = RequestBody.create(mode, MediaType.parse("text/plain"));

        String bearer = ApiClient.bearer(requireContext());

        ApiClient.get(requireContext())
                .createRoomWithPdf(bearer, filePart, questionsCountPart, timePerQuestionPart, difficultyPart, modePart)
                .enqueue(new Callback<Map<String, Object>>() {
                    @Override
                    public void onResponse(Call<Map<String, Object>> call, Response<Map<String, Object>> response) {
                        setUploading(false);
                        tempFile.delete();

                        if (response.isSuccessful() && response.body() != null) {
                            String roomCode = String.valueOf(response.body().get("room_code"));
                            if (getActivity() == null) return;
                            Intent intent = new Intent(getActivity(), LobbyActivity.class);
                            // The room already exists on the backend (created via REST above);
                            // the host still has to join_room over the WebSocket, same as any
                            // other room. A "single" mode room auto-starts as soon as it does.
                            intent.putExtra("mode", "single".equals(mode) ? "solo" : "join");
                            intent.putExtra("roomCode", roomCode);
                            startActivity(intent);
                        } else if (response.code() == 401) {
                            Toast.makeText(getContext(), "Your session expired - please sign out and sign in again", Toast.LENGTH_LONG).show();
                        } else {
                            Toast.makeText(getContext(), "Could not generate the quiz from this document (error " + response.code() + ")", Toast.LENGTH_LONG).show();
                        }
                    }

                    @Override
                    public void onFailure(Call<Map<String, Object>> call, Throwable t) {
                        setUploading(false);
                        tempFile.delete();
                        Toast.makeText(getContext(), "Upload failed: " + t.getMessage(), Toast.LENGTH_LONG).show();
                    }
                });
    }

    private void setUploading(boolean uploading) {
        if (getView() == null) return;
        pdfProgressRow.setVisibility(uploading ? View.VISIBLE : View.GONE);
        btnSolo.setEnabled(!uploading);
        btnCreateRoom.setEnabled(!uploading);
        btnChooseFile.setEnabled(!uploading);
    }

    private File copyUriToTempFile(Uri uri, String displayName) {
        try {
            InputStream in = requireContext().getContentResolver().openInputStream(uri);
            if (in == null) return null;

            String safeName = displayName != null ? displayName : "document";
            File out = new File(requireContext().getCacheDir(), System.currentTimeMillis() + "_" + safeName);

            try (FileOutputStream fos = new FileOutputStream(out)) {
                byte[] buffer = new byte[8192];
                int read;
                while ((read = in.read(buffer)) != -1) {
                    fos.write(buffer, 0, read);
                }
            }
            in.close();
            return out;
        } catch (Exception e) {
            return null;
        }
    }

    private String guessMimeType(String filename) {
        String lower = filename.toLowerCase();
        if (lower.endsWith(".pdf")) return "application/pdf";
        if (lower.endsWith(".docx")) return "application/vnd.openxmlformats-officedocument.wordprocessingml.document";
        return "text/plain";
    }
}

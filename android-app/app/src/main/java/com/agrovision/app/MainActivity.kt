package com.agrovision.app

import android.content.ActivityNotFoundException
import android.content.Context
import android.content.Intent
import android.content.res.ColorStateList
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Matrix
import android.media.ExifInterface
import android.net.ConnectivityManager
import android.net.Network
import android.net.NetworkCapabilities
import android.net.Uri
import android.os.Bundle
import android.speech.tts.TextToSpeech
import android.view.View
import android.view.ViewGroup
import android.view.inputmethod.EditorInfo
import android.view.inputmethod.InputMethodManager
import android.widget.EditText
import android.widget.FrameLayout
import android.widget.ImageView
import android.widget.TextView
import android.widget.Toast
import androidx.activity.result.PickVisualMediaRequest
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.appcompat.app.AppCompatDelegate
import androidx.core.content.ContextCompat
import androidx.core.content.FileProvider
import androidx.core.os.LocaleListCompat
import androidx.core.widget.NestedScrollView
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.google.android.material.bottomnavigation.BottomNavigationView
import com.google.android.material.button.MaterialButton
import com.google.android.material.chip.Chip
import com.google.android.material.chip.ChipGroup
import com.google.android.material.dialog.MaterialAlertDialogBuilder
import com.google.android.material.progressindicator.LinearProgressIndicator
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.MainScope
import kotlinx.coroutines.cancel
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONObject
import org.tensorflow.lite.Interpreter
import org.tensorflow.lite.support.common.ops.NormalizeOp
import org.tensorflow.lite.support.image.ImageProcessor
import org.tensorflow.lite.support.image.TensorImage
import org.tensorflow.lite.support.image.ops.ResizeOp
import java.io.File
import java.util.Locale
import java.util.concurrent.TimeUnit

class MainActivity : AppCompatActivity() {

    private lateinit var bottomNav: BottomNavigationView
    private lateinit var sectionDetect: View
    private lateinit var sectionSchemes: NestedScrollView
    private lateinit var sectionVoice: View
    private lateinit var sectionChat: View
    private lateinit var offlineIndicator: View
    private lateinit var btnLanguage: MaterialButton

    private lateinit var btnSelect: MaterialButton
    private lateinit var btnCapture: MaterialButton
    private lateinit var btnAnalyze: MaterialButton
    private lateinit var btnSpeak: MaterialButton
    private lateinit var progress: LinearProgressIndicator
    private lateinit var previewImage: ImageView
    private lateinit var previewEmpty: View
    private lateinit var tvStatus: TextView
    private lateinit var resultCard: View
    private lateinit var tvChip: TextView
    private lateinit var tvResultTitle: TextView
    private lateinit var tvResultCrop: TextView
    private lateinit var tvResultNote: TextView
    private lateinit var tvResultAlt: TextView

    private lateinit var schemesList: RecyclerView
    private lateinit var tvSchemesEmpty: TextView
    private lateinit var inputSchemeQuestion: EditText
    private lateinit var btnSchemeAdvisor: MaterialButton
    private lateinit var schemeAnswerCard: View
    private lateinit var tvSchemeAdvisorResult: TextView

    private lateinit var chatList: RecyclerView
    private lateinit var chatInput: EditText
    private lateinit var btnSendChat: MaterialButton
    private lateinit var chatSuggestions: ChipGroup
    private lateinit var chatSuggestionsScroll: View

    private val scope = MainScope()
    private var selectedImageUri: Uri? = null
    private var selectedBitmap: Bitmap? = null
    private var interpreter: Interpreter? = null
    private var tts: TextToSpeech? = null
    private var isModelLoaded = false
    private var lastSpoken = ""
    private var networkCallback: ConnectivityManager.NetworkCallback? = null
    private val chatMessages = mutableListOf<ChatMessage>()
    private val schemeItems = mutableListOf<SchemeItem>()

    private val modelFile = "plant_disease_model.tflite"
    private val labelsFile = "plant_disease_labels.json"
    private var inputSize = 112
    private var labels: List<String> = emptyList()
    private var classesPerCrop: Map<String, Int> = emptyMap()
    private val httpClient = OkHttpClient.Builder()
        .connectTimeout(30, TimeUnit.SECONDS)
        .readTimeout(60, TimeUnit.SECONDS)
        .build()

    private lateinit var tempPhotoFile: File

    private val pickMedia = registerForActivityResult(ActivityResultContracts.PickVisualMedia()) { uri ->
        if (uri != null) updateSelectedImage(uri)
    }

    private val captureMedia = registerForActivityResult(ActivityResultContracts.TakePicture()) { success ->
        if (success) updateSelectedImage(Uri.fromFile(tempPhotoFile))
        else Toast.makeText(this, getString(R.string.toast_capture_cancelled), Toast.LENGTH_SHORT).show()
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)
        bindViews()

        prepareTempFile()
        initializeModel()
        initializeTts()
        setupLanguageButton()
        setupBottomNav()
        setupSchemes()
        setupChat()
        monitorNetwork()

        btnSelect.setOnClickListener {
            pickMedia.launch(PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.ImageOnly))
        }
        btnCapture.setOnClickListener {
            val uri = FileProvider.getUriForFile(this, "${packageName}.fileprovider", tempPhotoFile)
            captureMedia.launch(uri)
        }
        btnAnalyze.setOnClickListener { analyzeSelectedImage() }
        btnSpeak.setOnClickListener {
            if (lastSpoken.isNotBlank()) speak(lastSpoken)
            else Toast.makeText(this, getString(R.string.toast_no_result), Toast.LENGTH_SHORT).show()
        }
        findViewById<View>(R.id.btnCallHelpline).setOnClickListener { dialHelpline() }
        btnSendChat.setOnClickListener { sendChatMessage(chatInput.text.toString()) }
        chatInput.setOnEditorActionListener { _, actionId, _ ->
            if (actionId == EditorInfo.IME_ACTION_SEND) {
                sendChatMessage(chatInput.text.toString())
                true
            } else false
        }
        btnSchemeAdvisor.setOnClickListener { requestSchemeAdvice() }

        savedInstanceState?.getString(STATE_IMAGE)?.let { updateSelectedImage(Uri.parse(it)) }
    }

    override fun onSaveInstanceState(outState: Bundle) {
        super.onSaveInstanceState(outState)
        selectedImageUri?.let { outState.putString(STATE_IMAGE, it.toString()) }
    }

    override fun onRestoreInstanceState(savedInstanceState: Bundle) {
        super.onRestoreInstanceState(savedInstanceState)
        showSection(bottomNav.selectedItemId)
    }

    private fun bindViews() {
        bottomNav = findViewById(R.id.bottomNav)
        sectionDetect = findViewById(R.id.sectionDetect)
        sectionSchemes = findViewById(R.id.sectionSchemes)
        sectionVoice = findViewById(R.id.sectionVoice)
        sectionChat = findViewById(R.id.sectionChat)
        offlineIndicator = findViewById(R.id.offlineIndicator)
        btnLanguage = findViewById(R.id.btnLanguage)

        btnSelect = findViewById(R.id.btnSelectImage)
        btnCapture = findViewById(R.id.btnCaptureImage)
        btnAnalyze = findViewById(R.id.btnAnalyze)
        btnSpeak = findViewById(R.id.btnSpeak)
        progress = findViewById(R.id.progressBar)
        previewImage = findViewById(R.id.imageViewPreview)
        previewEmpty = findViewById(R.id.previewEmpty)
        tvStatus = findViewById(R.id.tvStatus)
        resultCard = findViewById(R.id.resultCard)
        tvChip = findViewById(R.id.tvChip)
        tvResultTitle = findViewById(R.id.tvResultTitle)
        tvResultCrop = findViewById(R.id.tvResultCrop)
        tvResultNote = findViewById(R.id.tvResultNote)
        tvResultAlt = findViewById(R.id.tvResultAlt)

        schemesList = findViewById(R.id.schemesList)
        tvSchemesEmpty = findViewById(R.id.tvSchemesEmpty)
        inputSchemeQuestion = findViewById(R.id.inputSchemeQuestion)
        btnSchemeAdvisor = findViewById(R.id.btnSchemeAdvisor)
        schemeAnswerCard = findViewById(R.id.schemeAnswerCard)
        tvSchemeAdvisorResult = findViewById(R.id.tvSchemeAdvisorResult)

        chatList = findViewById(R.id.chatList)
        chatInput = findViewById(R.id.inputChat)
        btnSendChat = findViewById(R.id.btnSendChat)
        chatSuggestions = findViewById(R.id.chatSuggestions)
        chatSuggestionsScroll = findViewById(R.id.chatSuggestionsScroll)
    }

    // ---------------------------------------------------------------- Leaf scan

    private fun prepareTempFile() {
        val storageDir = File(externalCacheDir ?: cacheDir, "Images")
        if (!storageDir.exists()) storageDir.mkdirs()
        tempPhotoFile = File(storageDir, "temp_capture.jpg")
    }

    private fun loadLabelsFromAssets(): List<String> {
        assets.open(labelsFile).use { stream ->
            val arr = JSONArray(stream.bufferedReader().readText())
            return List(arr.length()) { i -> arr.getString(i) }
        }
    }

    private fun initializeModel() {
        try {
            labels = loadLabelsFromAssets()
            val modelBuffer = org.tensorflow.lite.support.common.FileUtil.loadMappedFile(this, modelFile)
            interpreter = Interpreter(modelBuffer)

            val inShape = interpreter!!.getInputTensor(0).shape()
            val outShape = interpreter!!.getOutputTensor(0).shape()
            inputSize = inShape[1]
            val outputClasses = outShape.last()
            check(labels.size == outputClasses) {
                "Label count (${labels.size}) does not match model outputs ($outputClasses)"
            }
            classesPerCrop = labels.groupingBy { cropOf(it) }.eachCount()
            isModelLoaded = true
        } catch (e: Exception) {
            isModelLoaded = false
            showStatus(getString(R.string.status_model_error, e.message ?: ""), isError = true)
        }
    }

    /** Decodes a photo no larger than ~1024 px on its longest side, upright. Runs off the main thread. */
    private fun decodePhoto(uri: Uri): Bitmap? {
        val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
        contentResolver.openInputStream(uri)?.use { BitmapFactory.decodeStream(it, null, bounds) }
        if (bounds.outWidth <= 0 || bounds.outHeight <= 0) return null

        var sample = 1
        while (maxOf(bounds.outWidth, bounds.outHeight) / (sample * 2) >= 1024) sample *= 2
        val options = BitmapFactory.Options().apply { inSampleSize = sample }
        val decoded = contentResolver.openInputStream(uri)?.use { BitmapFactory.decodeStream(it, null, options) }
            ?: return null

        val orientation = try {
            contentResolver.openInputStream(uri)?.use {
                ExifInterface(it).getAttributeInt(ExifInterface.TAG_ORIENTATION, ExifInterface.ORIENTATION_NORMAL)
            } ?: ExifInterface.ORIENTATION_NORMAL
        } catch (_: Exception) {
            ExifInterface.ORIENTATION_NORMAL
        }
        val matrix = Matrix()
        when (orientation) {
            ExifInterface.ORIENTATION_ROTATE_90 -> matrix.postRotate(90f)
            ExifInterface.ORIENTATION_ROTATE_180 -> matrix.postRotate(180f)
            ExifInterface.ORIENTATION_ROTATE_270 -> matrix.postRotate(270f)
            ExifInterface.ORIENTATION_FLIP_HORIZONTAL -> matrix.postScale(-1f, 1f)
            ExifInterface.ORIENTATION_FLIP_VERTICAL -> matrix.postScale(1f, -1f)
            else -> return decoded
        }
        return Bitmap.createBitmap(decoded, 0, 0, decoded.width, decoded.height, matrix, true)
    }

    private fun updateSelectedImage(uri: Uri) {
        selectedImageUri = uri
        resultCard.visibility = View.GONE
        scope.launch {
            val bitmap = withContext(Dispatchers.IO) {
                try { decodePhoto(uri) } catch (_: Exception) { null }
            }
            if (bitmap == null) {
                selectedBitmap = null
                btnAnalyze.isEnabled = false
                showStatus(getString(R.string.status_failed, ""), isError = true)
                return@launch
            }
            selectedBitmap = bitmap
            previewImage.setImageBitmap(bitmap)
            previewImage.visibility = View.VISIBLE
            previewEmpty.visibility = View.GONE
            btnAnalyze.isEnabled = isModelLoaded
            if (isModelLoaded) showStatus(getString(R.string.status_ready))
        }
    }

    private fun analyzeSelectedImage() {
        val bitmap = selectedBitmap ?: return
        if (!isModelLoaded) return
        progress.visibility = View.VISIBLE
        btnAnalyze.isEnabled = false
        resultCard.visibility = View.GONE
        showStatus(getString(R.string.status_running))

        scope.launch {
            try {
                val scores = withContext(Dispatchers.Default) { classify(bitmap) }
                showStatus(null)
                showVerdict(decide(scores))
            } catch (e: Exception) {
                showStatus(getString(R.string.status_failed, e.message ?: ""), isError = true)
            } finally {
                progress.visibility = View.GONE
                btnAnalyze.isEnabled = true
            }
        }
    }

    private fun classify(bitmap: Bitmap): FloatArray {
        // Same preprocessing as the web scan: the model was trained with nearest-neighbour
        // resizing, which is clearly more accurate than bilinear. Large photos are shrunk
        // with smoothing first, because nearest-neighbour on a 12 MP photo skips most pixels.
        val processorBuilder = ImageProcessor.Builder()
        if (maxOf(bitmap.width, bitmap.height) > 256) {
            processorBuilder.add(ResizeOp(256, 256, ResizeOp.ResizeMethod.BILINEAR))
        }
        val imageProcessor = processorBuilder
            .add(ResizeOp(inputSize, inputSize, ResizeOp.ResizeMethod.NEAREST_NEIGHBOR))
            .add(NormalizeOp(0.0f, 255.0f))
            .build()

        var tensorImage = TensorImage(org.tensorflow.lite.DataType.FLOAT32)
        tensorImage.load(bitmap)
        tensorImage = imageProcessor.process(tensorImage)

        val output = Array(1) { FloatArray(labels.size) }
        interpreter?.run(tensorImage.buffer, output)
        return output[0]
    }

    /** Label such as "Tomato___Early_blight" -> crop "Tomato". */
    private fun cropOf(label: String) = label.substringBefore("___")

    private fun prettyCrop(label: String) = cropOf(label).replace('_', ' ').trim()

    private fun prettyCondition(label: String): String {
        val raw = label.substringAfter("___", label).replace('_', ' ').trim()
        return raw.replaceFirstChar { it.uppercase() }
    }

    private enum class Kind { HEALTHY, POSSIBLE, UNSURE }

    private data class Verdict(
        val kind: Kind,
        val title: String,
        val crop: String?,
        val note: String,
        val alternatives: String?,
        val spoken: String
    )

    /**
     * Turns raw scores into something honest. The model was trained on lab photos and is often
     * wrong on field photos, so a weak answer is shown as "not sure", and crops with a single
     * class (it cannot tell healthy from sick) are never judged. No percentage is shown.
     */
    private fun decide(scores: FloatArray): Verdict {
        val order = scores.indices.sortedByDescending { scores[it] }
        val best = order.first()
        val label = labels[best]
        val crop = prettyCrop(label)

        if ((classesPerCrop[cropOf(label)] ?: 0) < 2) {
            return Verdict(
                Kind.UNSURE, getString(R.string.result_single_title, crop), null,
                getString(R.string.result_single_note), null, getString(R.string.speak_unsure)
            )
        }
        if (scores[best] < MIN_CONFIDENCE) {
            return Verdict(
                Kind.UNSURE, getString(R.string.result_unsure_title), null,
                getString(R.string.result_unsure_note), null, getString(R.string.speak_unsure)
            )
        }

        val others = order.drop(1).filter { scores[it] >= 0.10f && labels[it].isNotBlank() }.take(2)
            .joinToString(", ") { "${prettyCrop(labels[it])}: ${prettyCondition(labels[it]).lowercase()}" }
            .ifBlank { null }
        val alternatives = others?.let { getString(R.string.result_alt, it) }

        return if (label.contains("healthy", ignoreCase = true)) {
            Verdict(
                Kind.HEALTHY, getString(R.string.chip_healthy), crop,
                getString(R.string.result_healthy_note), alternatives,
                getString(R.string.speak_healthy, crop)
            )
        } else {
            val condition = prettyCondition(label)
            Verdict(
                Kind.POSSIBLE, condition, crop,
                getString(R.string.result_disease_note), alternatives,
                getString(R.string.speak_possible, crop, condition.lowercase())
            )
        }
    }

    private fun showVerdict(v: Verdict) {
        val (chipText, background, text) = when (v.kind) {
            Kind.HEALTHY -> Triple(R.string.chip_healthy, R.color.leaf_wash, R.color.leaf_deep)
            Kind.POSSIBLE -> Triple(R.string.chip_possible, R.color.soil_wash, R.color.soil)
            Kind.UNSURE -> Triple(R.string.chip_unsure, R.color.surface_2, R.color.ink_2)
        }
        tvChip.text = getString(chipText)
        tvChip.backgroundTintList = ColorStateList.valueOf(ContextCompat.getColor(this, background))
        tvChip.setTextColor(ContextCompat.getColor(this, text))

        tvResultTitle.text = v.title
        tvResultCrop.text = v.crop?.let { getString(R.string.result_crop, it) }
        tvResultCrop.visibility = if (v.crop == null) View.GONE else View.VISIBLE
        tvResultNote.text = v.note
        tvResultAlt.text = v.alternatives
        tvResultAlt.visibility = if (v.alternatives == null) View.GONE else View.VISIBLE

        lastSpoken = v.spoken
        resultCard.visibility = View.VISIBLE
        (sectionDetect as NestedScrollView).post {
            (sectionDetect as NestedScrollView).smoothScrollTo(0, resultCard.top)
        }
        speak(v.spoken)
    }

    private fun showStatus(message: String?, isError: Boolean = false) {
        tvStatus.visibility = if (message.isNullOrBlank()) View.GONE else View.VISIBLE
        tvStatus.text = message
        tvStatus.setTextColor(ContextCompat.getColor(this, if (isError) R.color.danger else R.color.ink_3))
    }

    // ---------------------------------------------------------------- Navigation

    private fun setupBottomNav() {
        bottomNav.setOnItemSelectedListener { item ->
            showSection(item.itemId)
            true
        }
        bottomNav.selectedItemId = R.id.nav_detect
        showSection(R.id.nav_detect)
    }

    private fun showSection(itemId: Int) {
        sectionDetect.visibility = if (itemId == R.id.nav_detect) View.VISIBLE else View.GONE
        sectionSchemes.visibility = if (itemId == R.id.nav_schemes) View.VISIBLE else View.GONE
        sectionVoice.visibility = if (itemId == R.id.nav_voice) View.VISIBLE else View.GONE
        sectionChat.visibility = if (itemId == R.id.nav_chat) View.VISIBLE else View.GONE
        if (itemId != R.id.nav_chat) hideKeyboard()
    }

    private fun hideKeyboard() {
        val imm = getSystemService(Context.INPUT_METHOD_SERVICE) as InputMethodManager
        imm.hideSoftInputFromWindow(window.decorView.windowToken, 0)
    }

    private fun setupLanguageButton() {
        val tags = listOf("en", "hi", "te")
        val names = listOf("English", "हिन्दी", "తెలుగు")
        val current = AppCompatDelegate.getApplicationLocales().toLanguageTags().substringBefore('-')
            .ifBlank { Locale.getDefault().language }
        val currentIndex = tags.indexOf(current).coerceAtLeast(0)
        btnLanguage.text = names[currentIndex]
        btnLanguage.setOnClickListener {
            MaterialAlertDialogBuilder(this)
                .setTitle(R.string.lang_label)
                .setSingleChoiceItems(names.toTypedArray(), currentIndex) { dialog, which ->
                    dialog.dismiss()
                    if (which != currentIndex) {
                        AppCompatDelegate.setApplicationLocales(LocaleListCompat.forLanguageTags(tags[which]))
                    }
                }
                .show()
        }
    }

    private fun dialHelpline() {
        val intent = Intent(Intent.ACTION_DIAL, Uri.parse("tel:" + getString(R.string.helpline_number)))
        try {
            startActivity(intent)
        } catch (_: ActivityNotFoundException) {
            Toast.makeText(this, getString(R.string.helpline_number), Toast.LENGTH_LONG).show()
        }
    }

    // ---------------------------------------------------------------- Schemes

    private fun setupSchemes() {
        schemesList.layoutManager = LinearLayoutManager(this)
        schemesList.adapter = SchemeAdapter(schemeItems, ::explainSchemeWithAi, ::openUrl)
        loadSchemesFromServer()
    }

    private fun loadSchemesFromServer() {
        if (!isNetworkAvailable()) {
            tvSchemesEmpty.setText(R.string.schemes_failed)
            return
        }
        scope.launch {
            val loaded = withContext(Dispatchers.IO) {
                try {
                    val request = Request.Builder().url("$baseUrl/api/schemes").get().build()
                    httpClient.newCall(request).execute().use { response ->
                        val arr = JSONObject(response.body?.string().orEmpty()).getJSONArray("schemes")
                        List(arr.length()) { i ->
                            val o = arr.getJSONObject(i)
                            SchemeItem(
                                id = o.getString("id"),
                                title = o.getString("name"),
                                desc = o.getString("description"),
                                benefit = o.getString("benefit"),
                                url = o.optString("url", "")
                            )
                        }
                    }
                } catch (_: Exception) {
                    null
                }
            }
            if (loaded.isNullOrEmpty()) {
                tvSchemesEmpty.setText(R.string.schemes_failed)
            } else {
                schemeItems.clear()
                schemeItems.addAll(loaded)
                schemesList.adapter?.notifyDataSetChanged()
                tvSchemesEmpty.visibility = View.GONE
            }
        }
    }

    private val baseUrl: String get() = getString(R.string.api_base_url).trimEnd('/')

    private fun requestSchemeAdvice() {
        val message = inputSchemeQuestion.text.toString().trim()
        if (message.isEmpty()) {
            Toast.makeText(this, getString(R.string.schemes_need_text), Toast.LENGTH_SHORT).show()
            return
        }
        hideKeyboard()
        if (!isNetworkAvailable()) {
            showSchemeAnswer(getString(R.string.chat_offline))
            return
        }
        btnSchemeAdvisor.isEnabled = false
        showSchemeAnswer(getString(R.string.schemes_ai_thinking))
        scope.launch {
            val reply = withContext(Dispatchers.IO) { postSchemeAdvise(message) }
            btnSchemeAdvisor.isEnabled = true
            showSchemeAnswer(reply)
        }
    }

    private fun explainSchemeWithAi(item: SchemeItem) {
        if (!isNetworkAvailable()) {
            showSchemeAnswer(getString(R.string.chat_offline))
            return
        }
        showSchemeAnswer(getString(R.string.schemes_ai_thinking))
        scope.launch {
            val reply = withContext(Dispatchers.IO) { postSchemeExplain(item.id) }
            showSchemeAnswer("${item.title}\n\n$reply")
        }
    }

    private fun showSchemeAnswer(text: String) {
        tvSchemeAdvisorResult.text = text
        schemeAnswerCard.visibility = View.VISIBLE
        sectionSchemes.post { sectionSchemes.smoothScrollTo(0, schemeAnswerCard.top) }
    }

    private fun postJson(path: String, body: JSONObject): String {
        val request = Request.Builder()
            .url("$baseUrl$path")
            .post(body.toString().toRequestBody("application/json".toMediaType()))
            .build()
        return httpClient.newCall(request).execute().use { response ->
            val raw = response.body?.string().orEmpty()
            val json = JSONObject(if (raw.isNotBlank()) raw else "{}")
            json.optString("response").ifBlank { getString(R.string.chat_error_generic) }
        }
    }

    private fun postSchemeAdvise(message: String): String = try {
        postJson(
            "/api/schemes/advise",
            JSONObject().put("message", message).put("state", "India")
                .put("crop", "not specified").put("land_acres", "not specified")
        )
    } catch (_: Exception) {
        getString(R.string.chat_error_generic)
    }

    private fun postSchemeExplain(schemeId: String): String = try {
        postJson("/api/schemes/$schemeId/explain", JSONObject().put("state", "India"))
    } catch (_: Exception) {
        getString(R.string.chat_error_generic)
    }

    private fun openUrl(url: String) {
        try {
            startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
        } catch (_: Exception) {
            Toast.makeText(this, url, Toast.LENGTH_LONG).show()
        }
    }

    // ---------------------------------------------------------------- Chat

    private fun setupChat() {
        chatList.layoutManager = LinearLayoutManager(this).apply { stackFromEnd = true }
        chatList.adapter = ChatAdapter(chatMessages)
        chatMessages.add(ChatMessage(fromUser = false, text = getString(R.string.chat_welcome)))

        listOf(R.string.chat_suggest_1, R.string.chat_suggest_2, R.string.chat_suggest_3).forEach { res ->
            val chip = Chip(this).apply {
                text = getString(res)
                isCheckable = false
                setOnClickListener { sendChatMessage(text.toString()) }
            }
            chatSuggestions.addView(chip)
        }
    }

    private fun isNetworkAvailable(): Boolean {
        val cm = getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager
        val network = cm.activeNetwork ?: return false
        val caps = cm.getNetworkCapabilities(network) ?: return false
        return caps.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)
    }

    private fun sendChatMessage(raw: String) {
        val text = raw.trim()
        if (text.isEmpty() || !btnSendChat.isEnabled) return
        chatInput.text.clear()
        chatSuggestionsScroll.visibility = View.GONE
        addChat(ChatMessage(fromUser = true, text = text))

        if (!isNetworkAvailable()) {
            addChat(ChatMessage(fromUser = false, text = getString(R.string.chat_offline)))
            return
        }

        btnSendChat.isEnabled = false
        val thinking = ChatMessage(fromUser = false, text = getString(R.string.chat_thinking))
        addChat(thinking)
        scope.launch {
            val reply = withContext(Dispatchers.IO) { fetchChatFromServer(text) }
            val index = chatMessages.indexOf(thinking)
            if (index >= 0) {
                chatMessages.removeAt(index)
                chatList.adapter?.notifyItemRemoved(index)
            }
            btnSendChat.isEnabled = true
            addChat(ChatMessage(fromUser = false, text = reply))
        }
    }

    private fun addChat(message: ChatMessage) {
        chatMessages.add(message)
        chatList.adapter?.notifyItemInserted(chatMessages.size - 1)
        chatList.scrollToPosition(chatMessages.size - 1)
    }

    private fun fetchChatFromServer(message: String): String = try {
        postJson("/api/chat", JSONObject().put("message", message))
    } catch (_: Exception) {
        getString(R.string.chat_error_generic)
    }

    // ---------------------------------------------------------------- Speech, network

    private fun initializeTts() {
        tts = TextToSpeech(this) { status ->
            if (status == TextToSpeech.SUCCESS) {
                tts?.language = Locale.getDefault()
            }
        }
    }

    private fun speak(text: String) {
        tts?.speak(text, TextToSpeech.QUEUE_FLUSH, null, "agrovision")
    }

    private fun monitorNetwork() {
        offlineIndicator.visibility = if (isNetworkAvailable()) View.GONE else View.VISIBLE
        val cm = getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager
        val callback = object : ConnectivityManager.NetworkCallback() {
            override fun onAvailable(network: Network) {
                runOnUiThread { offlineIndicator.visibility = View.GONE }
            }

            override fun onLost(network: Network) {
                runOnUiThread { offlineIndicator.visibility = View.VISIBLE }
            }
        }
        cm.registerDefaultNetworkCallback(callback)
        networkCallback = callback
    }

    // ---------------------------------------------------------------- Lists

    data class SchemeItem(
        val id: String,
        val title: String,
        val desc: String,
        val benefit: String,
        val url: String = ""
    )

    data class ChatMessage(val fromUser: Boolean, val text: String)

    inner class SchemeAdapter(
        private val items: List<SchemeItem>,
        private val onExplain: (SchemeItem) -> Unit,
        private val onOpen: (String) -> Unit
    ) : RecyclerView.Adapter<SchemeAdapter.SchemeVH>() {
        inner class SchemeVH(view: View) : RecyclerView.ViewHolder(view) {
            val title: TextView = view.findViewById(R.id.schemeTitle)
            val desc: TextView = view.findViewById(R.id.schemeDesc)
            val benefit: TextView = view.findViewById(R.id.schemeBenefit)
            val explain: View = view.findViewById(R.id.schemeExplain)
            val open: View = view.findViewById(R.id.schemeOpen)
        }

        override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): SchemeVH =
            SchemeVH(layoutInflater.inflate(R.layout.item_scheme, parent, false))

        override fun onBindViewHolder(holder: SchemeVH, position: Int) {
            val item = items[position]
            holder.title.text = item.title
            holder.desc.text = item.desc
            holder.benefit.text = item.benefit
            holder.explain.setOnClickListener { onExplain(item) }
            holder.open.visibility = if (item.url.isBlank()) View.GONE else View.VISIBLE
            holder.open.setOnClickListener { onOpen(item.url) }
        }

        override fun getItemCount(): Int = items.size
    }

    inner class ChatAdapter(private val items: List<ChatMessage>) : RecyclerView.Adapter<ChatAdapter.ChatVH>() {
        inner class ChatVH(view: View) : RecyclerView.ViewHolder(view) {
            val bubble: TextView = view.findViewById(R.id.chatBubble)
        }

        override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ChatVH =
            ChatVH(layoutInflater.inflate(R.layout.item_chat_message, parent, false))

        override fun onBindViewHolder(holder: ChatVH, position: Int) {
            val item = items[position]
            holder.bubble.text = item.text
            val params = holder.bubble.layoutParams as FrameLayout.LayoutParams
            if (item.fromUser) {
                params.gravity = android.view.Gravity.END
                holder.bubble.setBackgroundResource(R.drawable.bg_bubble_user)
                holder.bubble.setTextColor(ContextCompat.getColor(this@MainActivity, R.color.on_leaf))
            } else {
                params.gravity = android.view.Gravity.START
                holder.bubble.setBackgroundResource(R.drawable.bg_bubble_bot)
                holder.bubble.setTextColor(ContextCompat.getColor(this@MainActivity, R.color.ink))
            }
            holder.bubble.layoutParams = params
        }

        override fun getItemCount(): Int = items.size
    }

    override fun onDestroy() {
        super.onDestroy()
        scope.cancel()
        networkCallback?.let {
            (getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager).unregisterNetworkCallback(it)
        }
        interpreter?.close()
        tts?.shutdown()
    }

    companion object {
        private const val STATE_IMAGE = "selected_image"
        private const val MIN_CONFIDENCE = 0.5f
    }
}

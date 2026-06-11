package com.agrovision.app

import android.content.Context
import android.content.Intent
import android.graphics.Bitmap
import android.graphics.Color
import android.net.ConnectivityManager
import android.net.Network
import android.net.NetworkCapabilities
import android.net.Uri
import android.os.Bundle
import android.provider.MediaStore
import android.speech.tts.TextToSpeech
import android.view.View
import android.view.ViewGroup
import android.widget.EditText
import android.widget.ImageView
import android.widget.ProgressBar
import android.widget.TextView
import android.widget.Toast
import androidx.activity.result.PickVisualMediaRequest
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.appcompat.app.AppCompatDelegate
import androidx.core.content.FileProvider
import androidx.core.os.LocaleListCompat
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.google.android.material.bottomnavigation.BottomNavigationView
import com.google.android.material.button.MaterialButton
import com.google.android.material.button.MaterialButtonToggleGroup
import com.google.android.material.progressindicator.CircularProgressIndicator
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
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

    private lateinit var btnSelect: MaterialButton
    private lateinit var btnCapture: MaterialButton
    private lateinit var btnAnalyze: MaterialButton
    private lateinit var languageToggle: MaterialButtonToggleGroup
    private lateinit var btnSpeak: MaterialButton
    private lateinit var btnContrast: MaterialButton
    private lateinit var bottomNav: BottomNavigationView
    private lateinit var sectionDetect: View
    private lateinit var sectionSchemes: View
    private lateinit var sectionVoice: View
    private lateinit var sectionChat: View
    private lateinit var schemesList: RecyclerView
    private lateinit var inputSchemeQuestion: EditText
    private lateinit var btnSchemeAdvisor: MaterialButton
    private lateinit var tvSchemeAdvisorResult: TextView
    private lateinit var chatList: RecyclerView
    private lateinit var chatInput: EditText
    private lateinit var btnSendChat: MaterialButton
    private lateinit var offlineIndicator: View
    private lateinit var gaugeIndicator: CircularProgressIndicator
    private lateinit var imageView: ImageView
    private lateinit var tvResult: TextView
    private lateinit var progressBar: ProgressBar

    private var selectedImageUri: Uri? = null
    private var interpreter: Interpreter? = null
    private var tts: TextToSpeech? = null
    private var isHighContrast = false
    private var isModelLoaded = false
    private val chatMessages = mutableListOf<ChatMessage>()
    private val schemeItems = mutableListOf<SchemeItem>()

    private val MODEL_FILE = "plant_disease_model.tflite"
    private val LABELS_FILE = "plant_disease_labels.json"
    private var inputSize = 112
    private var labels: List<String> = emptyList()
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

        // Bind UI
        btnSelect = findViewById(R.id.btnSelectImage)
        btnCapture = findViewById(R.id.btnCaptureImage)
        btnAnalyze = findViewById(R.id.btnAnalyze)
        languageToggle = findViewById(R.id.languageToggle)
        btnSpeak = findViewById(R.id.btnSpeak)
        btnContrast = findViewById(R.id.btnContrast)
        bottomNav = findViewById(R.id.bottomNav)
        sectionDetect = findViewById(R.id.sectionDetect)
        sectionSchemes = findViewById(R.id.sectionSchemes)
        sectionVoice = findViewById(R.id.sectionVoice)
        sectionChat = findViewById(R.id.sectionChat)
        schemesList = findViewById(R.id.schemesList)
        inputSchemeQuestion = findViewById(R.id.inputSchemeQuestion)
        btnSchemeAdvisor = findViewById(R.id.btnSchemeAdvisor)
        tvSchemeAdvisorResult = findViewById(R.id.tvSchemeAdvisorResult)
        chatList = findViewById(R.id.chatList)
        chatInput = findViewById(R.id.inputChat)
        btnSendChat = findViewById(R.id.btnSendChat)
        offlineIndicator = findViewById(R.id.offlineIndicator)
        gaugeIndicator = findViewById(R.id.gaugeIndicator)
        imageView = findViewById(R.id.imageViewPreview)
        tvResult = findViewById(R.id.tvResult)
        progressBar = findViewById(R.id.progressBar)

        // Init
        initializeModel()
        initializeTts()
        prepareTempFile()
        setupLanguageToggle()
        setupBottomNav()
        setupSchemes()
        setupChat()
        monitorNetwork()

        // Listeners
        btnSelect.setOnClickListener {
            pickMedia.launch(PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.ImageOnly))
        }
        btnCapture.setOnClickListener {
            val uri = FileProvider.getUriForFile(this, "${packageName}.fileprovider", tempPhotoFile)
            captureMedia.launch(uri)
        }
        btnAnalyze.setOnClickListener {
            selectedImageUri?.let { uri ->
                if (isModelLoaded) analyzeImageLocally(uri)
            }
        }
        btnSpeak.setOnClickListener {
            val text = tvResult.text?.toString() ?: ""
            if (text.isNotBlank()) speak(text)
            else Toast.makeText(this, "No result to read", Toast.LENGTH_SHORT).show()
        }
        btnContrast.setOnClickListener { toggleContrast() }
        btnSendChat.setOnClickListener { sendChatMessage() }
        btnSchemeAdvisor.setOnClickListener { requestSchemeAdvice() }
    }

    private fun prepareTempFile() {
        val storageDir = File(externalCacheDir, "Images")
        if (!storageDir.exists()) storageDir.mkdirs()
        tempPhotoFile = File(storageDir, "temp_capture.jpg")
    }

    private fun updateSelectedImage(uri: Uri) {
        selectedImageUri = uri
        imageView.setImageURI(uri)
        imageView.clearColorFilter()
        if (isModelLoaded) {
            btnAnalyze.isEnabled = true
            tvResult.text = getString(R.string.image_ready)
            tvResult.setTextColor(Color.parseColor("#455A64"))
        }
    }

    private fun loadLabelsFromAssets(): List<String> {
        assets.open(LABELS_FILE).use { stream ->
            val arr = JSONArray(stream.bufferedReader().readText())
            return List(arr.length()) { i -> arr.getString(i) }
        }
    }

    private fun initializeModel() {
        try {
            labels = loadLabelsFromAssets()
            val modelBuffer = org.tensorflow.lite.support.common.FileUtil.loadMappedFile(this, MODEL_FILE)
            interpreter = Interpreter(modelBuffer)

            val inShape = interpreter!!.getInputTensor(0).shape()
            val outShape = interpreter!!.getOutputTensor(0).shape()
            inputSize = inShape[1]
            val outputClasses = outShape.last()

            if (labels.size != outputClasses) {
                throw IllegalStateException(
                    "Label count (${labels.size}) does not match model outputs ($outputClasses)"
                )
            }

            isModelLoaded = true
            tvResult.text = getString(R.string.model_loaded)
        } catch (e: Exception) {
            isModelLoaded = false
            tvResult.text = getString(R.string.model_error, e.message ?: "")
            tvResult.setTextColor(Color.RED)
        }
    }

    private fun analyzeImageLocally(uri: Uri) {
        progressBar.visibility = View.VISIBLE
        btnAnalyze.isEnabled = false
        tvResult.text = getString(R.string.scan_running)

        CoroutineScope(Dispatchers.IO).launch {
            try {
                val bitmap = MediaStore.Images.Media.getBitmap(contentResolver, uri)
                val imageProcessor = ImageProcessor.Builder()
                    .add(ResizeOp(inputSize, inputSize, ResizeOp.ResizeMethod.BILINEAR))
                    .add(NormalizeOp(0.0f, 255.0f))
                    .build()

                var tensorImage = TensorImage(org.tensorflow.lite.DataType.FLOAT32)
                tensorImage.load(bitmap)
                tensorImage = imageProcessor.process(tensorImage)

                val outputBuffer = Array(1) { FloatArray(labels.size) }
                interpreter?.run(tensorImage.buffer, outputBuffer)

                val scores = outputBuffer[0]
                val bestIdx = scores.indices.maxByOrNull { scores[it] } ?: 0
                val bestScore = scores[bestIdx]
                val bestLabel = if (bestIdx in labels.indices) labels[bestIdx] else "Unknown"

                withContext(Dispatchers.Main) {
                    displayResult(bestLabel, bestScore)
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    tvResult.text = getString(R.string.scan_failed, e.message ?: "")
                }
            } finally {
                withContext(Dispatchers.Main) {
                    progressBar.visibility = View.GONE
                    btnAnalyze.isEnabled = true
                }
            }
        }
    }

    private fun displayResult(label: String, confidence: Float) {
        val isHealthy = label.contains("healthy", ignoreCase = true)
        val color = if (isHealthy) "#2E7D32" else "#C62828"
        val prettyLabel = label.replace("___", " → ").replace("_", " ")

        val percent = (confidence * 100).toInt().coerceIn(0, 100)
        gaugeIndicator.max = 100
        gaugeIndicator.setProgressCompat(percent, true)

        val diagnosisLine = getString(R.string.diagnosis_prefix) + " " + prettyLabel
        val confidenceLine = getString(R.string.confidence_prefix) + " ${percent}%"
        val statusLine = if (isHealthy) getString(R.string.healthy_note) else getString(R.string.disease_note)
        val resultText = listOf(diagnosisLine, confidenceLine, "", statusLine).joinToString("\n")

        tvResult.text = resultText
        tvResult.setTextColor(Color.parseColor(color))
        speak(resultText)
    }

    private fun setupBottomNav() {
        bottomNav.setOnItemSelectedListener { item ->
            sectionDetect.visibility = if (item.itemId == R.id.nav_detect) View.VISIBLE else View.GONE
            sectionSchemes.visibility = if (item.itemId == R.id.nav_schemes) View.VISIBLE else View.GONE
            sectionVoice.visibility = if (item.itemId == R.id.nav_voice) View.VISIBLE else View.GONE
            sectionChat.visibility = if (item.itemId == R.id.nav_chat) View.VISIBLE else View.GONE
            true
        }
        bottomNav.selectedItemId = R.id.nav_detect
    }

    private fun setupSchemes() {
        schemesList.layoutManager = LinearLayoutManager(this)
        schemesList.adapter = SchemeAdapter(schemeItems) { item -> explainSchemeWithAi(item) }
        loadSchemesFromServer()
    }

    private fun loadSchemesFromServer() {
        if (!isNetworkAvailable()) return
        CoroutineScope(Dispatchers.IO).launch {
            try {
                val baseUrl = getString(R.string.api_base_url).trimEnd('/')
                val request = Request.Builder().url("$baseUrl/api/schemes").get().build()
                httpClient.newCall(request).execute().use { response ->
                    val raw = response.body?.string().orEmpty()
                    val arr = JSONObject(raw).getJSONArray("schemes")
                    val loaded = mutableListOf<SchemeItem>()
                    for (i in 0 until arr.length()) {
                        val o = arr.getJSONObject(i)
                        loaded.add(
                            SchemeItem(
                                id = o.getString("id"),
                                title = o.getString("name"),
                                desc = o.getString("description"),
                                benefit = o.getString("benefit"),
                                url = o.optString("url", "")
                            )
                        )
                    }
                    withContext(Dispatchers.Main) {
                        schemeItems.clear()
                        schemeItems.addAll(loaded)
                        schemesList.adapter?.notifyDataSetChanged()
                    }
                }
            } catch (_: Exception) {
                withContext(Dispatchers.Main) {
                    if (schemeItems.isEmpty()) {
                        schemeItems.add(
                            SchemeItem(
                                "pm-kisan",
                                "PM-KISAN",
                                "₹6,000/year — connect to server for full list",
                                "₹6,000/year",
                                "https://pmkisan.gov.in"
                            )
                        )
                        schemesList.adapter?.notifyDataSetChanged()
                    }
                }
            }
        }
    }

    private fun requestSchemeAdvice() {
        val message = inputSchemeQuestion.text.toString().trim()
        if (message.isEmpty()) {
            Toast.makeText(this, getString(R.string.schemes_advisor_hint), Toast.LENGTH_SHORT).show()
            return
        }
        if (!isNetworkAvailable()) {
            tvSchemeAdvisorResult.text = getString(R.string.chat_offline)
            tvSchemeAdvisorResult.visibility = View.VISIBLE
            return
        }
        btnSchemeAdvisor.isEnabled = false
        tvSchemeAdvisorResult.text = getString(R.string.schemes_ai_thinking)
        tvSchemeAdvisorResult.visibility = View.VISIBLE
        CoroutineScope(Dispatchers.IO).launch {
            val reply = postSchemeAdvise(message)
            withContext(Dispatchers.Main) {
                btnSchemeAdvisor.isEnabled = true
                tvSchemeAdvisorResult.text = reply
            }
        }
    }

    private fun explainSchemeWithAi(item: SchemeItem) {
        if (!isNetworkAvailable()) {
            Toast.makeText(this, getString(R.string.chat_offline), Toast.LENGTH_LONG).show()
            return
        }
        tvSchemeAdvisorResult.text = getString(R.string.schemes_ai_thinking)
        tvSchemeAdvisorResult.visibility = View.VISIBLE
        CoroutineScope(Dispatchers.IO).launch {
            val reply = postSchemeExplain(item.id)
            withContext(Dispatchers.Main) {
                tvSchemeAdvisorResult.text = "${item.title}\n\n$reply"
            }
        }
    }

    private fun postSchemeAdvise(message: String): String {
        return try {
            val baseUrl = getString(R.string.api_base_url).trimEnd('/')
            val body = JSONObject()
                .put("message", message)
                .put("state", "India")
                .put("crop", "not specified")
                .put("land_acres", "not specified")
                .toString()
            val request = Request.Builder()
                .url("$baseUrl/api/schemes/advise")
                .post(body.toRequestBody("application/json".toMediaType()))
                .build()
            httpClient.newCall(request).execute().use { response ->
                val json = JSONObject(response.body?.string().orEmpty())
                json.optString("response", json.optString("error", getString(R.string.chat_error_generic)))
            }
        } catch (e: Exception) {
            getString(R.string.chat_error_generic) + " (" + (e.message ?: "") + ")"
        }
    }

    private fun postSchemeExplain(schemeId: String): String {
        return try {
            val baseUrl = getString(R.string.api_base_url).trimEnd('/')
            val body = JSONObject().put("state", "India").toString()
            val request = Request.Builder()
                .url("$baseUrl/api/schemes/$schemeId/explain")
                .post(body.toRequestBody("application/json".toMediaType()))
                .build()
            httpClient.newCall(request).execute().use { response ->
                val json = JSONObject(response.body?.string().orEmpty())
                json.optString("response", json.optString("error", getString(R.string.chat_error_generic)))
            }
        } catch (e: Exception) {
            getString(R.string.chat_error_generic)
        }
    }

    private fun setupChat() {
        chatList.layoutManager = LinearLayoutManager(this)
        chatList.adapter = ChatAdapter(chatMessages)
        chatMessages.add(ChatMessage("assistant", getString(R.string.chat_welcome)))
        chatList.adapter?.notifyItemInserted(0)
    }

    private fun isNetworkAvailable(): Boolean {
        val cm = getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager
        val network = cm.activeNetwork ?: return false
        val caps = cm.getNetworkCapabilities(network) ?: return false
        return caps.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)
    }

    private fun sendChatMessage() {
        val text = chatInput.text.toString().trim()
        if (text.isEmpty()) return
        chatMessages.add(ChatMessage("user", text))
        chatInput.text.clear()
        chatList.adapter?.notifyItemInserted(chatMessages.size - 1)
        chatList.scrollToPosition(chatMessages.size - 1)

        if (!isNetworkAvailable()) {
            appendAssistantMessage(getString(R.string.chat_offline))
            return
        }

        btnSendChat.isEnabled = false
        appendAssistantMessage(getString(R.string.chat_thinking))
        val thinkingIndex = chatMessages.size - 1
        CoroutineScope(Dispatchers.IO).launch {
            val reply = fetchChatFromServer(text)
            withContext(Dispatchers.Main) {
                if (thinkingIndex in chatMessages.indices) {
                    chatMessages.removeAt(thinkingIndex)
                    chatList.adapter?.notifyItemRemoved(thinkingIndex)
                }
                btnSendChat.isEnabled = true
                appendAssistantMessage(reply)
            }
        }
    }

    private fun appendAssistantMessage(text: String) {
        chatMessages.add(ChatMessage("assistant", text))
        chatList.adapter?.notifyItemInserted(chatMessages.size - 1)
        chatList.scrollToPosition(chatMessages.size - 1)
    }

    private fun fetchChatFromServer(message: String): String {
        return try {
            val baseUrl = getString(R.string.api_base_url).trimEnd('/')
            val body = JSONObject().put("message", message).toString()
            val request = Request.Builder()
                .url("$baseUrl/api/chat")
                .post(body.toRequestBody("application/json".toMediaType()))
                .build()
            httpClient.newCall(request).execute().use { response ->
                val raw = response.body?.string().orEmpty()
                val json = JSONObject(if (raw.isNotBlank()) raw else "{}")
                when {
                    json.has("response") -> json.getString("response")
                    json.has("error") -> json.optString("error") + ": " + json.optString("details", "")
                    else -> getString(R.string.chat_error_generic)
                }
            }
        } catch (e: Exception) {
            getString(R.string.chat_error_generic) + " (" + (e.message ?: "network") + ")"
        }
    }

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

    private fun toggleContrast() {
        isHighContrast = !isHighContrast
        AppCompatDelegate.setDefaultNightMode(
            if (isHighContrast) AppCompatDelegate.MODE_NIGHT_YES else AppCompatDelegate.MODE_NIGHT_NO
        )
        Toast.makeText(this, if (isHighContrast) "High contrast ON" else "Standard view", Toast.LENGTH_SHORT).show()
    }

    private fun monitorNetwork() {
        val cm = getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager
        cm.registerDefaultNetworkCallback(object : ConnectivityManager.NetworkCallback() {
            override fun onAvailable(network: Network) {
                runOnUiThread { offlineIndicator.visibility = View.GONE }
            }
            override fun onLost(network: Network) {
                runOnUiThread { offlineIndicator.visibility = View.VISIBLE }
            }
        })
    }

    private fun setupLanguageToggle() {
        languageToggle.check(R.id.btnLangEn)
        languageToggle.addOnButtonCheckedListener { _, checkedId, isChecked ->
            if (!isChecked) return@addOnButtonCheckedListener
            val tag = when (checkedId) {
                R.id.btnLangHi -> "hi"
                R.id.btnLangTe -> "te"
                else -> "en"
            }
            val locales = LocaleListCompat.forLanguageTags(tag)
            AppCompatDelegate.setApplicationLocales(locales)
        }
    }

    data class SchemeItem(
        val id: String,
        val title: String,
        val desc: String,
        val benefit: String,
        val url: String = ""
    )
    data class ChatMessage(val sender: String, val text: String)

    inner class SchemeAdapter(
        private val items: List<SchemeItem>,
        private val onItemClick: (SchemeItem) -> Unit
    ) : RecyclerView.Adapter<SchemeAdapter.SchemeVH>() {
        inner class SchemeVH(view: View) : RecyclerView.ViewHolder(view) {
            val title: TextView = view.findViewById(R.id.schemeTitle)
            val desc: TextView = view.findViewById(R.id.schemeDesc)
            val benefit: TextView = view.findViewById(R.id.schemeBenefit)
        }

        override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): SchemeVH {
            val view = layoutInflater.inflate(R.layout.item_scheme, parent, false)
            return SchemeVH(view)
        }

        override fun onBindViewHolder(holder: SchemeVH, position: Int) {
            val item = items[position]
            holder.title.text = item.title
            holder.desc.text = item.desc
            holder.benefit.text = item.benefit
            holder.itemView.setOnClickListener { onItemClick(item) }
        }

        override fun getItemCount(): Int = items.size
    }

    inner class ChatAdapter(private val items: List<ChatMessage>) : RecyclerView.Adapter<ChatAdapter.ChatVH>() {
        inner class ChatVH(view: View) : RecyclerView.ViewHolder(view) {
            val bubble: TextView = view.findViewById(R.id.chatBubble)
        }

        override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ChatVH {
            val view = layoutInflater.inflate(R.layout.item_chat_message, parent, false)
            return ChatVH(view)
        }

        override fun onBindViewHolder(holder: ChatVH, position: Int) {
            val item = items[position]
            holder.bubble.text = item.text
            holder.bubble.textAlignment = if (item.sender == "user") View.TEXT_ALIGNMENT_TEXT_END else View.TEXT_ALIGNMENT_TEXT_START
        }

        override fun getItemCount(): Int = items.size
    }

    override fun onDestroy() {
        super.onDestroy()
        interpreter?.close()
        tts?.shutdown()
    }
}

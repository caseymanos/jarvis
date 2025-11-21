class AudioProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this.bufferSize = 512;
    this.buffer = [];
  }

  process(inputs, outputs, parameters) {
    const input = inputs[0];

    if (input && input.length > 0) {
      const channelData = input[0];

      for (let i = 0; i < channelData.length; i++) {
        this.buffer.push(channelData[i]);
      }

      if (this.buffer.length >= this.bufferSize) {
        const audioData = new Float32Array(this.buffer.splice(0, this.bufferSize));

        this.port.postMessage({
          type: 'audio',
          buffer: audioData,
          timestamp: currentTime
        });
      }
    }

    return true;
  }
}

registerProcessor('audio-processor', AudioProcessor);

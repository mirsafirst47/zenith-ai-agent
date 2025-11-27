import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Phone, BarChart3, Globe, Zap } from "lucide-react";

export default function Home() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="container mx-auto px-4 py-20">
        <div className="text-center max-w-4xl mx-auto">
          <div className="flex justify-center mb-6">
            <Phone className="h-16 w-16 text-blue-600" />
          </div>
          
          <h1 className="text-5xl font-bold text-gray-900 mb-6">
            Zenith AI Phone Agent
          </h1>
          
          <p className="text-xl text-gray-600 mb-8">
            Multilingual AI customer service that never sleeps. Handle calls in 5 languages, 
            book appointments, and delight customers 24/7.
          </p>
          
          <div className="flex gap-4 justify-center">
            <Link href="/dashboard">
              <Button size="lg" className="text-lg">
                Go to Dashboard
              </Button>
            </Link>
          </div>
        </div>

        <div className="grid md:grid-cols-4 gap-6 mt-20">
          <div className="bg-white p-6 rounded-xl shadow-md">
            <Globe className="h-10 w-10 text-blue-600 mb-4" />
            <h3 className="font-semibold text-lg mb-2">5 Languages</h3>
            <p className="text-gray-600 text-sm">
              English, Spanish, Chinese, French, Russian
            </p>
          </div>
          
          <div className="bg-white p-6 rounded-xl shadow-md">
            <Zap className="h-10 w-10 text-yellow-600 mb-4" />
            <h3 className="font-semibold text-lg mb-2">24/7 Available</h3>
            <p className="text-gray-600 text-sm">
              Never miss a call, day or night
            </p>
          </div>
          
          <div className="bg-white p-6 rounded-xl shadow-md">
            <BarChart3 className="h-10 w-10 text-green-600 mb-4" />
            <h3 className="font-semibold text-lg mb-2">Analytics</h3>
            <p className="text-gray-600 text-sm">
              Track performance and insights
            </p>
          </div>
          
          <div className="bg-white p-6 rounded-xl shadow-md">
            <Phone className="h-10 w-10 text-purple-600 mb-4" />
            <h3 className="font-semibold text-lg mb-2">Smart Routing</h3>
            <p className="text-gray-600 text-sm">
              Escalates to humans when needed
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
